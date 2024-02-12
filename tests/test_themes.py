import pathlib
import os

import pytest

from corna import enums
from corna.controls import theme_control
from corna.db import models
from corna.utils import image_proc, mkdir, secure, utils
from tests.shared_data import ASSET_DIR, single_user


@pytest.fixture(autouse=True)
def _all_required_themes_stubs(tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for themes
    related testing.
    """
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


def _theme(**kwargs):
    theme_data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "description": "This theme does super cool theme stuff.",
    }
    if kwargs:
        theme_data.update(**kwargs)

    return theme_data


def create_theme_helper(client, **kwargs):
    """Helper to create themes for testing none create endpoints."""

    resp = client.post("api/v1/themes", data=_theme(**kwargs))
    assert resp.status_code == 201


@pytest.fixture(name="cwfc")
def _client_with_fake_cookie(client):
    client.set_cookie(
        "/", enums.SessionNames.SESSION.value,
        secure.sign("I am some fake cookie")
    )
    return client


def test_themes_dir_exists():
    """
    This will be useful if we ever change the filesystem structure
    because we've essentially hardcoded the path to the themes directory.

    Furthermore, we use the CORNA_ROOT variable in utils to test it
    because the theme directory patch fixture is auto-used and it would
    be a pain to manually pass it into every test just because of this one
    test.
    """
    assert (utils.CORNA_ROOT / "themes").exists()


def test_add_theme(session, client, login):

    resp = client.post("/api/v1/themes", data=_theme())
    assert resp.status_code == 201

    # grab db data
    user = session.query(models.UserTable).first()
    theme = session.query(models.Themes).first()
    assert theme.uuid != None
    assert theme.name == "new fancy theme"
    assert theme.description == "This theme does super cool theme stuff."
    assert theme.path == None
    assert theme.status == enums.ThemeReviewState.UNKNOWN.value
    assert theme.creator_user_id == user.uuid


def test_add_theme_with_path(session, client, login):

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.html"
    path.touch()

    resp = client.post("/api/v1/themes", data=_theme(path="index.html"))
    assert resp.status_code == 201

    # grab db data
    user = session.query(models.UserTable).first()
    theme = session.query(models.Themes).first()
    assert theme.uuid != None
    assert theme.name == "new fancy theme"
    assert theme.description == "This theme does super cool theme stuff."
    assert theme.path == "index.html"
    assert theme.status == enums.ThemeReviewState.MERGED.value
    assert theme.creator_user_id == user.uuid


@pytest.mark.parametrize("fd,expected", 
    [
        ("index.html", 201),
        ("index.css", 201),
        ("index.js", 201),
        ("index.py", 400),
        ("index.php", 400),
        ("index.cpp", 400),
        ("index.java", 400),
        ("index", 400),
    ]
)
def test_theme_with_bad_extensions(client, login, fd, expected):
    path_ = pathlib.Path(theme_control.THEMES_DIR) / fd
    path_.touch()

    resp = client.post("/api/v1/themes", data=_theme(path=fd))
    assert resp.status_code == expected


@pytest.mark.parametrize("fd,expected",
    [
        ("some/very/long/path/index.html", 201),
        ("some/long.path/with.periods/index.html", 201),
        ("some/long.path/with.periods/index.css", 201),
        ("some/long.path/with.periods/index.js", 201),
        ("some/long.path/with.periods/index.php", 400),
        ("some/long.path/with.periods/index.py", 400),
        ("long/path/with.period/but/no/extension/index", 400),

    ]
)
def test_theme_with_weirdly_long_path(client, login, fd, expected):

    path = theme_control.THEMES_DIR / fd
    mkdir(path)

    resp = client.post("/api/v1/themes", data=_theme(path=fd))
    assert resp.status_code == expected


def test_user_has_cookie_but_is_not_found(cwfc):

    resp = cwfc.post("api/v1/themes", data=_theme())
    assert resp.status_code == 401


def test_anon_user_create_theme(client):
    """
    Here we test the standard 'this person is not logged in'
    scenario. This should always fail and return 401.
    """
    resp = client.post("/api/v1/themes", data=_theme())
    assert resp.status_code == 401
    assert resp.json["message"] == "Login required for this action"


def test_not_logged_in_user_create_theme(client, session, login):
    """
    This is testing the scenario that the user ID of the current
    user does not match the creator ID. This is a valid action as these
    theme endpoints will eventually only be used by admin system users.
    """
    # register new user
    resp = client.post("/api/v1/auth/register",
        json=single_user(
            email_address="ergo@proxy.rondo",
            password="Re-l",
            user_name="proxy1"
        )
    )
    assert resp.status_code == 201

    resp = client.post("/api/v1/themes", data=_theme(creator="proxy1"))
    assert resp.status_code == 201

    # grab db data
    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "proxy1")
        .one_or_none()
    )
    assert user is not None

    theme = session.query(models.Themes).first()
    assert theme.uuid != None
    assert theme.name == "new fancy theme"
    assert theme.description == "This theme does super cool theme stuff."
    assert theme.path == None
    assert theme.status == enums.ThemeReviewState.UNKNOWN.value
    assert theme.creator_user_id == user.uuid


def test_create_theme_with_thumbnail(session, client, login):
    resp = client.post("/api/v1/themes", data=_theme(
        thumbnail=(ASSET_DIR / "anders-jilden.jpg").open("rb")))
    assert resp.status_code == 201

    # grab db data
    user = session.query(models.UserTable).first()
    theme = session.query(models.Themes).first()
    assert theme.uuid != None
    assert theme.name == "new fancy theme"
    assert theme.description == "This theme does super cool theme stuff."
    assert theme.path == None
    assert theme.status == enums.ThemeReviewState.UNKNOWN.value
    assert theme.creator_user_id == user.uuid
    assert theme.thumbnail is not None

    expected_path = image_proc.PICTURE_DIR / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    thumbnail_uuid = theme.thumbnail
    image = session.query(models.Images).first()
    basename = expected_path.listdir()[0].basename
    assert image.uuid == thumbnail_uuid
    assert image.path == f"thi/sis/afa/kehash12345/{basename}"



def test_create_theme_multiple_thumbnail(session, client, login):

    resp = client.post(
        "/api/v1/themes",
        data=_theme(
            thumbnail=[
                (ASSET_DIR / "anders-jilden.jpg").open("rb"),
                (ASSET_DIR / "anders-jilden.jpg").open("rb")
            ]
        ))
    assert resp.status_code == 422
    assert resp.json["message"] == "This URI expects no greater than 1 file(s)"


def test_add_theme_duplicate(client, session, login):

    create_theme_helper(client)

    resp = client.post("/api/v1/themes", data=_theme())
    assert resp.status_code == 400
    assert resp.json["message"] == "Theme already exists"


def test_status_update_with_path(client, session, login):

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.html"
    path.touch()

    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "path": "index.html",
        "status": "unknown",
    }
    create_theme_helper(client, path="index.html")

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 200

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == data["creator"])
        .one_or_none()
    )
    theme = session.query(models.Themes).first()
    assert theme.uuid != None
    assert theme.name == "new fancy theme"
    assert theme.description == "This theme does super cool theme stuff."
    assert theme.path == "index.html"
    assert theme.status == enums.ThemeReviewState.UNKNOWN.value
    assert theme.creator_user_id == user.uuid


def test_update_status_user_with_cookie_but_no_session(cwfc):
    
    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "path": "index.html",
        "status": "unknown",
    }

    resp = cwfc.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 401


def test_no_theme_exists(client, login):
    
    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "path": "index.html",
        "status": "unknown",
    }

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 400
    assert resp.json["message"] == "No theme exists matching given details"


def test_theme_creator_does_not_exist(client, login):

    data = {
        "creator": "no-existant-user",
        "name": "new fancy theme",
        "path": "index.html",
        "status": "unknown",
    }

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 401
    assert resp.json["message"] == "Theme creator does not exist"


def test_status_update_no_path_but_merged(client, login):

    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "status": "merged",
    }

    create_theme_helper(client)

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 400
    assert resp.json["message"] == "Cannot set status to merged without valid path"


def test_status_update_bad_path(client, login):

    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "status": "merged",
        "path": "index.php"
    }

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.php"
    path.touch()

    # we want to actually enter the user into the database
    create_theme_helper(client)

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 400
    assert resp.json["message"] == "Incorrect file type"


def test_anon_user_update_status(client):
    """
    Here we test the standard 'this person is not logged in'
    scenario. This should always fail and return 401.
    """
    data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "status": "merged",
        "path": "index.html"
    }

    resp = client.put("/api/v1/themes/status", json=data)
    assert resp.status_code == 401
    assert resp.json["message"] == "Login required for this action"


def test_get_theme_list(client, mocker, login):

    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )

    path = pathlib.Path(theme_control.THEMES_DIR) / "index.html"
    path.touch()

    create_theme_helper(
        client, path="index.html",
        thumbnail=(ASSET_DIR / "anders-jilden.jpg").open("rb"),
    )

    expected = {"themes": [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "name": "new fancy theme",
            "creator": "john_snow",
            "thumbnail": "https://api.mycorna.com/v1/media/download/abcdef",
            "description": "This theme does super cool theme stuff.",
        }
    ]}

    resp = client.get("/api/v1/themes")
    assert resp.status_code == 200

    actual = resp.json
    import pprint
    pprint.pprint(actual)
    assert actual == expected
