import pathlib

import pytest

from corna import enums
from corna.controls import theme_control
from corna.db import models
from corna.utils import secure, utils
from tests.shared_data import single_user


def _theme(**kwargs):
    theme_data = {
        "creator": "john_snow",
        "name": "new fancy theme",
        "description": "This theme does super cool theme stuff.",
    }
    if kwargs:
        theme_data.update(**kwargs)

    return theme_data


@pytest.fixture(name="cwfc")
def _client_with_fake_cookie(client):
    client.set_cookie(
        "/", enums.SessionNames.SESSION.value,
        secure.sign("I am some fake cookie")
    )
    return client


@pytest.fixture(autouse=True)
def _theme_dir_patch(tmpdir, monkeypatch):
     monkeypatch.setattr(theme_control, "THEMES_DIR", tmpdir.mkdir("themes"))


def test_add_theme(session, client, login):

    resp = client.post("/api/v1/themes", json=_theme())
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

    resp = client.post("/api/v1/themes", json=_theme(path="index.html"))
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

    resp = client.post("/api/v1/themes", json=_theme(path=fd))
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
    utils.mkdir(path)

    resp = client.post("/api/v1/themes", json=_theme(path=fd))
    assert resp.status_code == expected


def test_user_has_cookie_but_is_not_found(cwfc):

    resp = cwfc.post("api/v1/themes", json=_theme())
    assert resp.status_code == 401


def test_anon_user_create_theme(client):
    """
    Here we test the standard 'this person is not logged in'
    scenario. This should always fail and return 401.
    """
    resp = client.post("/api/v1/themes", json=_theme())
    assert resp.status_code == 401
    assert resp.json["message"] == "Login required for this action"


def test_not_logged_in_user_create_theme(client, session, login):
    """
    This is testing the scenario that the user ID of the current
    user does not match the creator ID. This is a valid action as these
    theme endpoints will eventually only be used by admin system users.
    """
    # register new user
    resp = client.post("/api/v1/register",
        json=single_user(
            email_address="ergo@proxy.rondo",
            password="Re-l",
            user_name="proxy1"
        )
    )
    assert resp.status_code == 201

    resp = client.post("/api/v1/themes", json=_theme(creator="proxy1"))
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
