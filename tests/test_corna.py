import pathlib

import pytest

from corna import enums
from corna.controls import corna_control as control
from corna.controls import theme_control
from corna.db import models
from corna.middleware import permissions as perms
from corna.utils.errors import NoneExistingUserError
from corna.utils import image_proc, secure
from tests.shared_data import ASSET_DIR, corna_info, single_user


@pytest.fixture(name="theme")
def _theme(client, tmpdir, mocker, monkeypatch, login):
    # create a theme for tests

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
    monkeypatch.setattr(
        theme_control,
        "THEMES_DIR",
        tmpdir.mkdir("themes")
    )

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.html"
    path.touch()

    # upload image
    image = (ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": "image"},
    )

    theme_data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "description": "This theme does super cool theme stuff.",
        "path": "index.html",
        "thumbnail": "abcdef",
    }

    resp = client.post("api/v1/themes", json=theme_data)
    assert resp.status_code == 201


def test_corna_create(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 201
    
    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["username"]

    # check permissions
    assert corna.permissions is not None
    assert corna.permissions == 449  # default role

    expected = {
        "change_theme": False,
        "comment": True,
        "delete": False,
        "edit": False,
        "follow": True,
        "like": True,
        "read": True,
        "change_permissions": False,
        "write": False,
    }

    assert perms.perms(corna.permissions) == expected


def test_when_user_not_logged_in(session):

    data = {
        "cookie": secure.sign("some-fake-cookie"),
        "title": corna_info["title"],
        "domain_name": corna_info["domain_name"],
        "permissions": [],
    }

    # an exception should be raised
    try:
        control.create(session, **data)
        assert False
    except NoneExistingUserError:
        assert True


def test_when_user_not_logged_in_client(client):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 401
    assert "Login required for this action" in resp.json["message"]


def test_user_attempt_with_invalid_cookie(client):
    client.set_cookie(
        "/",
        key=enums.SessionNames.SESSION.value,
        value="this-is-a-fake-cookie"
    )
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 401
    assert "Login required for this action" in resp.json["message"]


def test_user_already_has_corna(client, corna):
    resp = client.post(
        "/api/v1/corna/new-corna-name",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "User has pre-existing Corna"


def test_domain_name_not_unique(session, client, corna):
    # make new adhoc user
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new.email@tester.com",
            "password": "some-fake=password",
            "username": "nunu_user",
            }
        )
    assert resp.status_code == 201

    # login
    resp = client.post("/api/v1/auth/login",
        json={
            "email": "new.email@tester.com",
            "password": "some-fake=password",
        }
    )
    assert resp.status_code == 200
    # attempt to make corna
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 400
    assert resp.json["message"] == "Domain name in use"


def test_relationships(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={"title": corna_info["title"]},
    )
    assert resp.status_code == 201

    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )

    usr = (
        session.query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .one_or_none()
    )
    assert usr is not None
    assert corna.user is usr
    assert usr.corna[0] is corna



def test_domain_name_available_check__when_not_avail(client, corna):
    # the "corna" fixture creates this domain
    domain_name = "some-fake-domain"
    resp = client.get(f"/api/v1/corna/domain/available?domain_name={domain_name}")
    assert resp.status_code == 200

    expected = {
        "domain_name": domain_name,
        "available": False,
    }
    assert resp.json == expected


def test_domain_name_available_check__when_avail(client):
    domain_name = "some-fake-domain"
    resp = client.get(f"/api/v1/corna/domain/available?domain_name={domain_name}")
    assert resp.status_code == 200

    expected = {
        "domain_name": domain_name,
        "available": True,
    }
    assert resp.json == expected


def test_corna_with_about(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={
            "title": corna_info["title"],
            "about_me": "Hey this is my cool new Corna!",
        },
    )
    assert resp.status_code == 201
    
    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["username"]
    assert corna.about is not None

    assert len(session.query(models.TextContent).all()) == 1
    about = (
        session
        .query(models.TextContent)
        .filter(models.TextContent.uuid == corna.about)
        .one_or_none()
    )

    assert about is not None
    assert about.post_uuid is None
    assert about.post is None
    assert about.content == "Hey this is my cool new Corna!"


def test_create_corna_with_theme(session, client, login, theme):

    theme = session.query(models.Themes).first()
    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={
            "title": corna_info["title"],
            "about_me": "Hey this is my cool new Corna!",
            "theme_uuid": theme.uuid,
        },
    )
    assert resp.status_code == 201

    # check everything saved correctly in db
    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["username"]
    assert corna.about is not None

    assert len(session.query(models.TextContent).all()) == 1
    about = (
        session
        .query(models.TextContent)
        .filter(models.TextContent.uuid == corna.about)
        .one_or_none()
    )

    assert about is not None
    assert about.post_uuid is None
    assert about.post is None
    assert about.content == "Hey this is my cool new Corna!"

    theme = (
        session
        .query(models.Themes)
        .filter(models.Themes.uuid == corna.theme)
        .one_or_none()
    )

    assert theme is not None
    assert theme.name == "new fancy theme"


def test_corna_create__none_default_permissions(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={
            "title": corna_info["title"],
            "permissions": ["read", "write", "edit"]
        },
    )
    assert resp.status_code == 201

    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["username"]

    # check permissions
    assert corna.permissions is not None
    assert corna.permissions == 7

    expected = {
        "change_theme": False,
        "comment": False,
        "delete": False,
        "edit": True,
        "follow": False,
        "like": False,
        "read": True,
        "change_permissions": False,
        "write": True,
    }

    assert perms.perms(corna.permissions) == expected


def test_corna_create__private_corna(session, client, login):

    resp = client.post(
        f"/api/v1/corna/{corna_info['domain_name']}",
        json={
            "title": corna_info["title"],
            # for a private Corna, permissions field should not be missing
            # but posted with an empty list
            "permissions": []
        },
    )
    assert resp.status_code == 201

    assert len(session.query(models.CornaTable).all()) == 1
    corna = (
        session.query(models.CornaTable)
        .filter(models.CornaTable.domain_name == corna_info["domain_name"])
        .one_or_none()
    )
    assert corna is not None
    user = single_user()
    assert corna.user.username == user["username"]

    # check permissions
    assert corna.permissions is not None
    assert corna.permissions == 0

    expected = {
        "change_theme": False,
        "comment": False,
        "delete": False,
        "edit": False,
        "follow": False,
        "like": False,
        "read": False,
        "change_permissions": False,
        "write": False,
    }

    assert perms.perms(corna.permissions) == expected
