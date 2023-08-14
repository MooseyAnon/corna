import pytest

from corna import enums
from corna.db import models
from corna.utils import encodings, secure
from tests.shared_data import single_user


def test_regester(session, client):
    user_deets = single_user()
    resp = client.post("/api/v1/register", json=user_deets)
    assert resp.status_code == 201
    assert len(session.query(models.EmailTable).all()) == 1
    assert len(session.query(models.UserTable).all()) == 1

    # check correct things are saved
    em = session.query(models.EmailTable).get(user_deets["email_address"])
    assert em is not None
    assert em.email_address == user_deets["email_address"]
    # we shouldn't be able to get the password
    try:
        em.password
        assert False
    except ValueError:
        assert True

    usr = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == user_deets["user_name"])
        .one()
    )
    assert usr is not None
    assert usr.username == user_deets["user_name"]

    # check relationships are correct
    assert usr.email_address == user_deets["email_address"]
    assert usr.email == em


def test_email_in_use_register_attempt(client, user):

    # try create another account with same user deets
    user_deets = single_user()
    resp = client.post("/api/v1/register", json=user_deets)
    assert resp.status_code == 400
    assert resp.json["message"] == "Email address already has an account"


def test_login(session, client, user):

    user_deets = single_user()
    resp = client.post("/api/v1/login", json={
            "email_address": user_deets["email_address"],
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
    database_cookie = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie)
        .one()
    )
    assert database_cookie is not None
    assert database_cookie.user.username == user_deets["user_name"]

    user = session.query(models.UserTable).get(database_cookie.user_uuid)
    assert user is not None
    assert user.username == user_deets["user_name"]

    # check forign key relationship is correct
    assert database_cookie.user is user


def test_user_already_logged_in(session, client, login):

    user_deets = single_user()
    resp = client.post("/api/v1/login", json={
            "email_address": user_deets["email_address"],
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
    database_cookie = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie)
        .one()
    )
    assert database_cookie is not None
    assert database_cookie.user.username == user_deets["user_name"]

    user = session.query(models.UserTable).get(database_cookie.user_uuid)
    assert user is not None
    assert user.username == user_deets["user_name"]    


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

    resp = client.post("/api/v1/login", json={
            "email_address": email,
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
    resp = client.post("/api/v1/login", json={
            "email_address": user_deets["email_address"],
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
    resp = client.post("/api/v1/login", json={
            "email_address": user_deets["email_address"],
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
    resp = client.post("/api/v1/logout")
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
    resp = client.post("/api/v1/login", json={
            "email_address": user_deets["email_address"],
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

    unsigned_cookie, _ = secure.unsign(cookie)
    db_cookie = session.query(models.SessionTable).all()[0].cookie_id
    assert db_cookie == encodings.from_bytes(db_cookie)


def test_signing_similar_messages():

    m1 = "aaaaaaaaa"
    m2 = "aaaaaaaab"

    s1 = secure.sign(m1)
    s2 = secure.sign(m2)

    _, s1_sig = secure.unsign(s1)
    _, s2_sig = secure.unsign(s2)

    assert secure.verify(m1, s1_sig)
    assert secure.verify(m2, s2_sig)

    assert not secure.verify(m1, s2_sig)
    assert not secure.verify(m2, s1_sig)


def test_unsign():

    sig = secure.sign("aaaaaaaaa")
    orig_message, _ = secure.unsign(sig)
    assert orig_message == b"aaaaaaaaa"


def test_fake_message():
    message = "I am a fake message"
    assert secure.verify(message, encodings.base64_encode(message)) == False

