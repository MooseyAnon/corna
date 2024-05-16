import pytest

from corna import enums
from corna.db import models
from corna.utils import secure, utils
from tests.shared_data import ASSET_DIR, single_user


def _upload_avatar(session):
    """Upload avatar directly to DB."""
    session.add(
        models.Images(
            uuid="00000000-0000-0000-0000-000000000000",
            hash="thisisafakehash12345",
        )
    )

    session.add(
        models.Media(
            uuid="00000000-0000-0000-0000-000000000000",
            url_extension="abcdef",
            path="thi/sis/afa/kehash12345",
            size=8096,
            created="2023-04-29T03:21:34",
            type="avatar",
            orphaned=True,
            image_uuid="00000000-0000-0000-0000-000000000000",
        )
    )
    session.commit()
    return "abcdef"


def test_regester(session, client):
    user_deets = single_user()
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 201
    assert len(session.query(models.EmailTable).all()) == 1
    assert len(session.query(models.UserTable).all()) == 1

    # check correct things are saved
    em = session.query(models.EmailTable).get(user_deets["email"])
    assert em is not None
    assert em.email_address == user_deets["email"]
    # we shouldn't be able to get the password
    try:
        em.password
        assert False
    except ValueError:
        assert True

    usr = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == user_deets["username"])
        .one()
    )
    assert usr is not None
    assert usr.username == user_deets["username"]

    # check relationships are correct
    assert usr.email_address == user_deets["email"]
    assert usr.email == em


def test_email_in_use_register_attempt(client, user):

    # try create another account with same user deets
    user_deets = single_user()
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 400
    assert resp.json["message"] == "Email address already has an account"


def test_register_with_avatar(session, client):
    avatar_slug = _upload_avatar(session)
    user_deets = single_user()
    user_deets["avatar"] = avatar_slug
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 201

    assert len(session.query(models.EmailTable).all()) == 1
    assert len(session.query(models.UserTable).all()) == 1
    assert session.query(models.Media).count() == 1
    assert session.query(models.Images).count() == 1

    # check correct things are saved
    em = session.query(models.EmailTable).get(user_deets["email"])
    assert em is not None
    assert em.email_address == user_deets["email"]
    # we shouldn't be able to get the password
    try:
        em.password
        assert False
    except ValueError:
        assert True

    usr = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == user_deets["username"])
        .one()
    )
    assert usr is not None
    assert usr.username == user_deets["username"]

    # check relationships are correct
    assert usr.email_address == user_deets["email"]
    assert usr.email == em

    avatar = session.query(models.Media).first()
    assert avatar.size > 1024
    assert avatar.type == "avatar"
    assert avatar.orphaned == False
    assert usr.avatar == avatar.uuid


def test_register__multiple_users_with_same_avatar(session, client):
    avatar_slug = _upload_avatar(session)
    user_deets = single_user()
    user_deets["avatar"] = avatar_slug
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 201

    # register user 2
    user_deets["email"] = "azor_ahi101@starkentaprise.wstro"
    user_deets["username"] = "john_snow12"
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 201

    assert session.query(models.EmailTable).count() == 2
    assert session.query(models.UserTable).count() == 2
    assert session.query(models.Media).count() == 1
    assert session.query(models.Images).count() == 1

    # ensure all users have same avatar
    avatar = session.query(models.Media).first()
    for user in session.query(models.UserTable).all():
        assert user.avatar == avatar.uuid


def test_login(session, client, user):

    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200

    # check cookie is set correctly
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is not None

    # check database bits are saved correctly
    assert len(session.query(models.SessionTable).all()) == 1
    # unsign cookie to search for it
    cookie = secure.decoded_message(cookie)
    database_cookie = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie)
        .one()
    )
    assert database_cookie is not None
    assert database_cookie.user.username == user_deets["username"]

    user = session.query(models.UserTable).get(database_cookie.user_uuid)
    assert user is not None
    assert user.username == user_deets["username"]

    # check forign key relationship is correct
    assert database_cookie.user is user


def test_user_already_logged_in(session, client, login):

    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is not None

    # ensure no new sessions were created
    assert len(session.query(models.SessionTable).all()) == 1
    # unsign cookie to search for it
    cookie = secure.decoded_message(cookie)
    database_cookie = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie)
        .one()
    )
    assert database_cookie is not None
    assert database_cookie.user.username == user_deets["username"]

    user = session.query(models.UserTable).get(database_cookie.user_uuid)
    assert user is not None
    assert user.username == user_deets["username"]    


@pytest.mark.parametrize("email,password,expected_status",
    [
        ("azor_ahi@starkentaprise.wstro", "badpassword", 400),
        ("azor_ahi@starkentaprise.wstro", "dany", 400),
        ("fake-email@email.com", "Dany", 404),
        ("fake-email@email.com", "badpassword", 404),
        ("azor_ahi@starkentaprise.wstro", "Dany", 200),
    ]
)
def test_login_attempt_with_wrong_creds(
    client, user, email, password, expected_status
):

    resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password,
        }
    )
    assert resp.status_code == expected_status


def test_headers(mocker, client, user):
    # test if we are updating headers correctly
    # this is used for adding cors and security headers
    mocker.patch(
        "corna.utils.secure.secure_headers",
        return_value={
            "fake-header-name": "fake-header-value",
            "fake-cors": "*",
        }
    )
    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200
    # cookie gets made first in the route function, we need to
    # make sure it does not get overwritten by the after_request
    # function
    # check there is a cookies in the cookie jar
    assert len(client.cookie_jar) > 0
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is not None

    # check if our headers are in the response headers
    assert resp.headers.get("fake-header-name") is not None
    assert resp.headers.get("fake-cors") is not None


def test_secure_cookie(session, client, user):

    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200
    # check if our secure headers are set properly
    cookie_perm_list = resp.headers.getlist("Set-Cookie")[0]
    assert "Secure" in cookie_perm_list
    assert "HttpOnly" in cookie_perm_list
    assert "SameSite=Lax" in cookie_perm_list


def test_logout(session, client, login):
    # ensure user sessions exists
    assert len(session.query(models.SessionTable).all()) == 1
    # check there is a cookies in the cookie jar
    assert len(client.cookie_jar) > 0
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is not None
    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # check db
    assert len(session.query(models.SessionTable).all()) == 0
    # make sure nothing got deleted from user table
    assert len(session.query(models.EmailTable).all()) == 1
    assert len(session.query(models.UserTable).all()) == 1
    # ensure cookie is removed
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is None


def test_new_session_starts_for_logged_in_user(session, client, login):

    # ensure user sessions exists
    assert len(session.query(models.SessionTable).all()) == 1
    # get session id
    first_session = session.query(models.SessionTable).all()[0].session_id
    # get cookie from cookie_jar
    assert len(client.cookie_jar) > 0
    first_cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert first_cookie is not None

    # try to log user in
    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200

    # check db
    assert len(session.query(models.SessionTable).all()) == 1
    new_session = session.query(models.SessionTable).all()[0].session_id
    assert new_session != first_session

    # check new cookie
    assert len(client.cookie_jar) > 0
    new_cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert new_cookie is not None
    assert new_cookie != first_cookie


def test_token_is_valid(session, client, login):

    # ensure user sessions exists
    assert len(session.query(models.SessionTable).all()) == 1

    # get cookie from cookie_jar
    assert len(client.cookie_jar) > 0
    cookie = next(
        (
            cookie.value
            for cookie in client.cookie_jar
            if cookie.name == enums.SessionNames.SESSION.value
        ),
        None
    )
    assert cookie is not None

    assert secure.is_valid(cookie)

    unsigned_cookie = secure.decoded_message(cookie)
    db_cookie = session.query(models.SessionTable).all()[0].cookie_id
    assert db_cookie == unsigned_cookie


def test_username_available_check__when_not_avail(client, user):
    # the "user" fixture creates this user
    username = "john_snow"
    resp = client.get(f"/api/v1/auth/username/available?username={username}")
    assert resp.status_code == 200

    expected = {
        "username": username,
        "available": False,
    }
    assert resp.json == expected


def test_username_available_check__when_avail(client):

    resp = client.get("/api/v1/auth/username/available?username=fake-name")
    assert resp.status_code == 200

    expected = {
        "username": "fake-name",
        "available": True,
    }
    assert resp.json == expected


def test_email_available_check__when_not_avail(client, user):
    # the "user" fixture creates this user
    email = "azor_ahi@starkentaprise.wstro"
    resp = client.get(f"/api/v1/auth/email/available?email={email}")
    assert resp.status_code == 200

    expected = {
        "email": email,
        "available": False,
    }
    assert resp.json == expected


def test_email_available_check__when_avail(client):
    resp = client.get(f"/api/v1/auth/email/available?email=fake@email.com")
    assert resp.status_code == 200

    expected = {
        "email": "fake@email.com",
        "available": True,
    }
    assert resp.json == expected


def test_login_status_check__loggedin(client, login):
    resp = client.get("/api/v1/auth/login_status")
    assert resp.status_code == 200

    expected = { "is_loggedin": True }
    assert resp.json == expected


def test_login_status_check__loggedout(client):
    resp = client.get("/api/v1/auth/login_status")
    assert resp.status_code == 200

    expected = { "is_loggedin": False }
    assert resp.json == expected


def test_preexisting_session_creates_restart(client, session, login):

    assert session.query(models.SessionTable).count() == 1
    prev_sesh = session.query(models.SessionTable).first().session_id

    client.cookie_jar.clear()
    # ensure we are not longer logged in
    resp = client.get("/api/v1/auth/login_status")
    assert resp.status_code == 200
    assert resp.json["is_loggedin"] == False

    # login again
    user_deets = single_user()
    resp = client.post("/api/v1/auth/login", json={
            "email": user_deets["email"],
            "password": user_deets["password"],
        }
    )
    assert resp.status_code == 200

    curr_sesh = session.query(models.SessionTable).first()

    assert curr_sesh.session_id != prev_sesh


def test_user_number_auto_increment(session, client):

    for i in range(1, 16):
        user_deets = {
            "email": f"azor_ahi{i}@starkentaprise.wstro",
            "password": "Dany",
            "username": f"john_snow{i}",
        }
        resp = client.post("/api/v1/auth/register", json=user_deets)
        assert resp.status_code == 201

        user = (
            session
            .query(models.UserTable)
            .filter(models.UserTable.username == f"john_snow{i}")
            .one()
        )

        assert user.number == i
