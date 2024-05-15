import json
import os

from freezegun import freeze_time
import pytest
import requests
import werkzeug

from corna import enums
from corna.controls import post_control
from corna.db import models
from corna.utils import utils, image_proc
from tests import shared_data


FROZEN_TIME = "2023-04-29T03:21:34"


def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f'{num:.1f} {x}'
        num /= 1024.0


def _upload_single_image(session, client, type_="image"):
    """Post a single image to the db/filesystem."""

    if type_ == "image":
        file = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")

    if type_ == "video":
        file = (shared_data.ASSET_DIR / "big-bunny.mp4").open("rb")

    resp = client.post(
        "/api/v1/media/upload",
        data={"image": file, "type": type_},
    )

    assert resp.status_code == 201
    assert session.query(models.Media).count() > 0

    return resp.json


@pytest.fixture(autouse=True)
def _all_post_based_stubs(request, tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for post
    related testing.
    """
    # this allows us to selectively create mocks, more info on request
    # objects go to link[1] and ctrl + f for "Using markers to pass data to
    # fixtures".
    #
    # [1] https://docs.pytest.org/en/7.4.x/how-to/fixtures.html
    if not ("nostubs" in request.keywords):
        mocker.patch(
            "corna.utils.utils.random_short_string",
            return_value="abcdef",
        )
    mocker.patch(
        "corna.utils.image_proc.hash_image",
        return_value="thisisafakehash12345",
    )
    monkeypatch.setattr(
        image_proc,
        "PICTURE_DIR",
        tmpdir.mkdir("assets"),
    )


@freeze_time(FROZEN_TIME)
def test_create_post(session, client, corna):
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=False,
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 201

    # check database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    corna = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.corna_info["domain_name"]
        )
        .one()
    )
    assert len(corna.posts) == 1

    post = session.query(models.PostTable).first()
    text = session.query(models.TextContent).first()
    
    # checking foreign key relationships
    assert post.corna_uuid == corna.uuid
    assert text.post_uuid == post.uuid

    assert post.type == out_post["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME
    assert post.user_uuid is not None

    assert text.content == out_post["content"]
    assert text.title == out_post["title"]


@freeze_time(FROZEN_TIME)
@pytest.mark.parametrize("with_image,expected", [(False, 400), (True, 201)])
def test_post_with_picture(session, client, corna, with_image, expected):
    # create image
    _upload_single_image(session, client)
    assets = image_proc.PICTURE_DIR
    out_post = shared_data.mock_post(
        type_="picture",
        with_content=True,
        with_title=True,
        with_image=with_image
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post
    )
    assert resp.status_code == expected

    # return early on no image text as there is nothing to check
    if not with_image: return

    expected_path = assets / "image" / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    image_basename = expected_path.listdir()[0].basename
    # ensure database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    corna = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.corna_info["domain_name"]
        )
        .one()
    )
    assert len(corna.posts) == 1
    post = session.query(models.PostTable).first()
    pic = session.query(models.Media).first()
    text = session.query(models.TextContent).first()

    # checking foreign key relationships
    assert post.corna_uuid == corna.uuid
    assert pic.post_uuid == post.uuid
    assert text.post_uuid == post.uuid

    assert post.type == out_post["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME

    assert text.content == out_post["content"]
    assert pic.size >= 1024
    assert pic.path == f"image/thi/sis/afa/kehash12345/{image_basename}"
    assert pic.url_extension == "abcdef"
    assert not pic.orphaned

    # ensure we do actually have an image and not just a media entry
    assert session.query(models.Images).count() == 1


def test_when_user_not_logged_in_client_text_post(session, client):
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post
    )
    assert resp.status_code == 401
    assert "Login required for this action" in resp.json["message"]


def test_when_user_not_logged_in_client(session, client):
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=False,
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        data=out_post
    )
    assert resp.status_code == 401
    assert "Login required for this action" in resp.json["message"]


def test_user_attempt_with_invalid_cookie(session, client, corna):
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=False,
    )
    client.set_cookie(
        "/",
        key=enums.SessionNames.SESSION.value,
        value="this-is-a-fake-cookie"
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post
    )
    assert resp.status_code == 401
    assert "Login required for this action" in resp.json["message"]


def test_linking_preloaded_images(session, client, corna):
    # create image
    _upload_single_image(session, client)

    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=True,
    )

    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 201

    # ensure we only still have one image and one post saved
    assert session.query(models.Images).count() == 1
    assert session.query(models.PostTable).count() == 1

    # ensure relationships are correct
    post = session.query(models.PostTable).first()
    assert post is not None
    assert len(post.media) == 1

    image = post.media[0]
    assert image.url_extension == "abcdef"
    assert image.orphaned == False


@pytest.mark.nostubs
def test_linking_multiple_images(session, client, corna):
    # create multiple image
    image_urls = []
    for _ in range(2):
        data = _upload_single_image(session, client)
        image_urls.append(data["url_extension"])

    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
    )
    # change uploaded images to our current list
    out_post["uploaded_images"] = image_urls
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 201

    # ensure we two images and one post saved
    assert session.query(models.Images).count() == 2
    assert session.query(models.PostTable).count() == 1

    # ensure relationships are correct
    post = session.query(models.PostTable).first()
    assert post is not None
    assert len(post.media) == 2

    for image in post.media:
        assert image.url_extension in image_urls
        assert image.orphaned == False


def test_linking_to_none_existing_image(session, client, corna):
    """We should raise error and not save anything."""

    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
    )
    out_post["uploaded_images"] = ["defghi"]
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "Unable to find file"

    # ensure nothing is saved
    assert session.query(models.PostTable).count() == 0


def test_post_with_no_title(session, client, corna):
    out_post = shared_data.mock_post(
        with_content=True,
    )

    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=shared_data.mock_post(with_content=True),
    )
    assert resp.status_code == 201
    assert session.query(models.PostTable).count() == 1
    assert session.query(models.TextContent).count() == 1


@freeze_time(FROZEN_TIME)
def test_none_owner_user_create_post(client, session, corna):
    from tests import test_checks

    test_checks._create_role_helper(client, name="default", permissions=["write"])
    test_checks._create_user_helper(session, "fake@user.com", "fake_user")
    test_checks._give_user_role_helper(client, "default",  "fake_user")

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "fake@user.com",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create post
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=False,
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 201

    # check database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    corna = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.corna_info["domain_name"]
        )
        .one()
    )
    assert len(corna.posts) == 1

    post = session.query(models.PostTable).first()
    text = session.query(models.TextContent).first()
    
    # checking foreign key relationships
    assert post.corna_uuid == corna.uuid
    assert text.post_uuid == post.uuid

    assert post.type == out_post["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME

    assert text.content == out_post["content"]
    assert text.title == out_post["title"]

    # get post creator
    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.uuid == post.user_uuid)
        .one()
    )
    assert user.username == "fake_user"


@freeze_time(FROZEN_TIME)
def test_none_owner_not_allowed_to_create_post(client, session, corna):
    from tests import test_checks
    test_checks._create_user_helper(session, "fake@user.com", "fake_user")

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "fake@user.com",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create post
    out_post = shared_data.mock_post(
        with_content=True,
        with_title=True,
        with_image=False,
    )
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post,
    )
    assert resp.status_code == 401
    assert resp.json["message"] == "User unauthorized to create posts"


@freeze_time(FROZEN_TIME)
def test_vido_post(session, client, mocker, corna):
    mocker.patch(
        "corna.utils.image_proc.random_hash",
        return_value="thisisafakestringhash",
    )

    assets = image_proc.PICTURE_DIR
    # create video
    _upload_single_image(session, client, type_="video")
    out_post = {
        "type": "video",
        "title": "this is a title of a post",
        "uploaded_images": ["abcdef"],
        "content": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed "
            "do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut "
            "enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi "
            "ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
            "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
            "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
            "culpa qui officia deserunt mollit anim id est laborum."
        )
    }
    resp = client.post(
        f"/api/v1/posts/{shared_data.corna_info['domain_name']}/post",
        json=out_post
    )
    assert resp.status_code == 201

    expected_path = assets / "video" / "thi/sis/afa/kestringhash"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    image_basename = expected_path.listdir()[0].basename
    # ensure database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    corna = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.corna_info["domain_name"]
        )
        .one()
    )
    assert len(corna.posts) == 1
    post = session.query(models.PostTable).first()
    vid = session.query(models.Media).first()
    text = session.query(models.TextContent).first()

    # checking foreign key relationships
    assert post.corna_uuid == corna.uuid
    assert vid.post_uuid == post.uuid
    assert text.post_uuid == post.uuid

    assert post.type == out_post["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME

    assert text.content == out_post["content"]
    assert vid.size >= 1024
    assert vid.path == f"video/thi/sis/afa/kestringhash/{image_basename}"
    assert vid.url_extension == "abcdef"
    assert not vid.orphaned
