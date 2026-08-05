import pathlib

import pytest

from corna import enums
from corna.controls import subdomain_control as control
from corna.controls import theme_control
from corna.db import models
from corna.utils import image_proc
from corna.utils import errors
from tests import shared_data


pytest.fixture(autouse=True)
def _all_media_based_stubs(request, tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for post
    related testing.
    """
    if not ("nostubs" in request.keywords):
        mocker.patch(
            "corna.utils.image_proc.hash_image",
            return_value="thisisafakehash12345",
        )
        mocker.patch(
            "corna.utils.utils.random_short_string",
            return_value="abcdef",
        )
    mocker.patch(
        "corna.utils.image_proc.random_hash",
        return_value="thisisafakestringhash",
    )
    assets = tmpdir.mkdir("assets")

    mocker.patch(
        "corna.utils.image_proc.get_workdir",
        return_value=assets,
    )


def _theme(**kwargs):
    theme_data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "description": "This theme does super cool theme stuff.",
    }
    if kwargs:
        theme_data.update(**kwargs)

    return theme_data


# We need to create a theme to test page building e2e
def create_theme_helper(client):
    """Helper to create themes for testing none create endpoints."""

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.html"
    path.touch()

    resp = client.post("api/v1/themes", json=_theme(path="index.html"))
    assert resp.status_code == 201


# We dont want to use fixtures for this because we want to change perms and test
# how the system behaves
def create_corna(client, session, corna_permissions=None):
    """Create a corna for subdomain tests."""
    create_theme_helper(client)
    theme = session.query(models.Themes).first()

    permissions = corna_permissions or []
    resp = client.post(
        f"/api/v1/corna/{shared_data.corna_info['domain_name']}",
        json={
            "title": shared_data.corna_info["title"],
            "permissions": permissions,
            "theme_uuid": theme.uuid,
        },
    )
    assert resp.status_code == 201


def create_post(
    session,
    client,
    *,
    type_="text",
    with_content=True,
    with_html=True,
    with_title=True,
    uploaded_images=None,
):
    """Create a post for subdomain contract tests."""
    payload = shared_data.mock_post(
        type_=type_,
        with_title=with_title,
        with_content=with_content,
        with_html=with_html,
        with_image=False,
    )
    if uploaded_images is not None:
        payload["uploaded_images"] = uploaded_images

    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=payload,
    )
    assert resp.status_code == 201

    post = (
        session
        .query(models.PostTable)
        .order_by(models.PostTable.created.desc())
        .first()
    )
    assert post is not None
    return post.url_extension


def _upload_media(client, filename, media_type):
    """Upload a media file and return its url extension."""
    with (shared_data.ASSET_DIR / filename).open("rb") as file_handle:
        resp = client.post(
            "/api/v1/media/upload",
            data={"image": file_handle, "type": media_type},
        )

    assert resp.status_code == 201
    return resp.json["url_extension"]


def _assert_default_listing_contract(listing, expected_size):
    """Assert the structural defaults of a listing payload."""
    assert listing.has_items == (expected_size > 0)
    assert listing.paging.has_next is False
    assert listing.paging.has_prev is False
    assert listing.paging.next_href is None
    assert listing.paging.prev_href is None
    assert listing.paging.current_page is None
    assert listing.paging.page_size == expected_size
    assert listing.paging.cursor is None
    assert listing.paging.next_cursor is None
    assert listing.render.is_fragment is False
    assert listing.render.fragment_name is None
    assert listing.behaviour.mode == "pagination"


def test_can_not_read_posts(session, client, login):
    # create private corna
    create_corna(client, session)

    try:
        control.build_page(session, shared_data.corna_info["domain_name"])
        assert False
    except errors.UnauthorizedActionError:
        # we shouldn't have permissions to see anything on the page
        assert True


def test_can_not_read_homepage(session, client, login):
    # create private corna
    create_corna(client, session)

    try:
        control.build_page(session, shared_data.corna_info["domain_name"])
        assert False
    except errors.UnauthorizedActionError:
        # we shouldn't have permissions to see anything on the page
        assert True


def test_can_not_read_homepage_but_no_corna(session):
    try:
        control.build_page(session, shared_data.corna_info["domain_name"])
        assert False
    except control.CornaNotFoundError:
        # we shouldn't have permissions to see anything on the page
        assert True


def test_user_can_read__read_perms_set_on_corna(session, client, login):
    create_corna(client, session, corna_permissions=["read"])

    try:
        # anyone should be able to read page
        control.build_page(session, shared_data.corna_info["domain_name"])
        assert True
    except errors.UnauthorizedActionError:
        assert False


def test_user_can_read__private_corna_but_owner(session, client, login):
    # create private corna
    create_corna(client, session)
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    try:
        # Owner should be able to see page
        control.build_page(
            session,
            shared_data.corna_info["domain_name"],
            cookie=cookie.value,
        )
        assert True
    except errors.UnauthorizedActionError:
        assert False


def test_single_post__can_not_read(session, client, login):
    # create private corna
    create_corna(client, session)

    try:
        control.single_post(
            session,
            "fake-url-extension",
            shared_data.corna_info["domain_name"],
        )
        assert False
    except errors.UnauthorizedActionError:
        # we shouldn't have permissions to see anything on the page
        assert True


def test_build_page_returns_empty_listing_contract(session, client, login):
    """Build page payloads should expose the new listing contract."""
    create_corna(client, session)
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    page = control.build_page(
        session,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert page.title == shared_data.corna_info["title"]
    assert page.theme_path
    assert page.listing.items == []
    _assert_default_listing_contract(page.listing, 0)


def test_build_page_text_post_includes_cover_media(
    monkeypatch, tmpdir, session, client, login):
    """Build page payloads should include parsed cover media in the listing."""

    create_corna(client, session)
    media_slug = _upload_media(client, "anders-jilden.jpg", "image")
    post_url = create_post(
        session,
        client,
        type_="text",
        uploaded_images=[media_slug],
    )
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    page = control.build_page(
        session,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert page.title == shared_data.corna_info["title"]
    assert page.theme_path
    assert len(page.listing.items) == 1
    assert page.listing.has_items is True

    post = page.listing.items[0]
    assert post.href == post_url
    assert post.type == "text"
    assert post.title == "this is a title of a post"
    assert post.domain_name == shared_data.corna_info["domain_name"]
    assert post.text_html is not None
    assert post.caption_html is None
    assert len(post.media) == 1
    assert post.media[0].type == "image"
    assert post.media[0].href
    assert post.media[0].width is not None
    assert post.media[0].height is not None
    assert post.media[0].aspect_ratio == image_proc.aspect_ratio(
        post.media[0].height,
        post.media[0].width,
    )

    _assert_default_listing_contract(page.listing, 1)


def test_single_post_image_parses_media_metadata(
    monkeypatch, tmpdir, session, client, login):
    """Image posts should expose parsed media metadata."""

    create_corna(client, session)
    media_slug = _upload_media(client, "anders-jilden.jpg", "image")
    post_url = create_post(
        session,
        client,
        type_="picture",
        with_content=False,
        with_html=False,
        uploaded_images=[media_slug],
    )
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    post, _ = control.single_post(
        session,
        post_url,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert len(post.media) == 1
    media = post.media[0]
    media_row = session.query(models.Media).filter_by(url_extension=media_slug).one()
    assert media.type == "image"
    assert media.href
    assert media.width == media_row.image.width
    assert media.height == media_row.image.height
    assert media.aspect_ratio == image_proc.aspect_ratio(media.height, media.width)


def test_single_post_video_parses_media_metadata(
    monkeypatch, tmpdir, session, client, login):
    """Video posts should expose parsed media metadata."""

    create_corna(client, session)
    media_slug = _upload_media(client, "big-bunny.mp4", "video")
    post_url = create_post(
        session,
        client,
        type_="video",
        with_content=False,
        with_html=False,
        uploaded_images=[media_slug],
    )
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    post, _ = control.single_post(
        session,
        post_url,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert len(post.media) == 1
    media = post.media[0]
    media_row = session.query(models.Media).filter_by(url_extension=media_slug).one()
    assert media.type == "video"
    assert media.href
    assert media.width == media_row.video.width
    assert media.height == media_row.video.height
    assert media.aspect_ratio == image_proc.aspect_ratio(media.height, media.width)


def test_single_post_text_only_has_no_media(session, client, login):
    """Text-only posts should not expose any media items."""
    create_corna(client, session)
    post_url = create_post(
        session,
        client,
        type_="text",
        with_content=True,
        with_html=True,
        uploaded_images=None,
    )
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    post, _ = control.single_post(
        session,
        post_url,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert post.media == []


def test_image_only_post(monkeypatch, tmpdir, session, client, login):
    """Image posts should expose parsed media metadata."""

    create_corna(client, session)
    media_slug = _upload_media(client, "anders-jilden.jpg", "image")
    post_url = create_post(
        session,
        client,
        type_="picture",
        with_content=False,
        with_html=False,
        with_title=False,
        uploaded_images=[media_slug],
    )
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    post, theme = control.single_post(
        session,
        post_url,
        shared_data.corna_info["domain_name"],
        cookie=cookie.value,
    )

    assert post.type == "picture"
    assert post.text_html == None
    assert post.caption_html == None
    assert post.title == None
    assert theme == "post.html"
    assert len(post.media) == 1
