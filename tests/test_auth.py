from datetime import timedelta

import pytest

from corna import enums
from corna.controls import auth_control
from corna.db import models
from corna.utils import get_utc_now, secure, utils
from tests.shared_data import ASSET_DIR, single_user


def _non_system_users(session):
    return session.query(models.UserTable).filter_by(is_system_account=False)


def _invite_from_join_url(session, join_url):
    token = join_url.removeprefix("join/")
    invite = (
        session
        .query(models.InviteTable)
        .filter(models.InviteTable.token_hash == secure.hash_invite_token(token))
        .one()
    )
    return token, invite


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
    assert _non_system_users(session).count() == 1

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

    # ensure invite was used and is associated properly
    assert not usr.is_system_account
    assert usr.invited_by_user_id != None

    invite = session.query(models.InviteTable).first()
    assert invite.redeemed_by_user_id == usr.uuid


def test_email_in_use_register_attempt(client, user):

    # try create another account with same user deets
    user_deets = single_user()
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 400
    assert resp.json["message"] == "Username or email are already in use."


def test_register_with_avatar(session, client):
    avatar_slug = _upload_avatar(session)
    user_deets = single_user()
    user_deets["avatar"] = avatar_slug
    resp = client.post("/api/v1/auth/register", json=user_deets)
    assert resp.status_code == 201

    assert len(session.query(models.EmailTable).all()) == 1
    assert _non_system_users(session).count() == 1
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
    assert _non_system_users(session).count() == 2
    assert session.query(models.Media).count() == 1
    assert session.query(models.Images).count() == 1

    # ensure all users have same avatar
    avatar = session.query(models.Media).first()
    for user in _non_system_users(session).all():
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
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    # check database bits are saved correctly
    assert len(session.query(models.SessionTable).all()) == 1
    # unsign cookie to search for it
    cookie = secure.decoded_message(cookie.value)
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
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    # ensure no new sessions were created
    assert len(session.query(models.SessionTable).all()) == 1
    # unsign cookie to search for it
    cookie = secure.decoded_message(cookie.value)
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
        ("fake-email@email.com", "Dany", 400),
        ("fake-email@email.com", "badpassword", 400),
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
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
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
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None
    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # check db
    assert len(session.query(models.SessionTable).all()) == 0
    # make sure nothing got deleted from user table
    assert len(session.query(models.EmailTable).all()) == 1
    assert _non_system_users(session).count() == 1
    # ensure cookie is removed
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is None


def test_new_session_starts_for_logged_in_user(session, client, login):

    # ensure user sessions exists
    assert len(session.query(models.SessionTable).all()) == 1
    # get session id
    first_session = session.query(models.SessionTable).all()[0].session_id
    # get cookie from cookie_jar
    first_cookie = client.get_cookie(enums.SessionNames.SESSION.value)
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
    new_cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert new_cookie is not None
    assert new_cookie.value != first_cookie.value


def test_token_is_valid(session, client, login):

    # ensure user sessions exists
    assert len(session.query(models.SessionTable).all()) == 1

    # get cookie from cookie_jar
    cookie = client.get_cookie(enums.SessionNames.SESSION.value)
    assert cookie is not None

    assert secure.is_valid(cookie.value)

    unsigned_cookie = secure.decoded_message(cookie.value)
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

    client._cookies.clear()
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

    # count how many system users there are
    sys_user_count = session.query(
        models.UserTable).filter_by(is_system_account=True).count()
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

        assert user.number == i + sys_user_count


@pytest.mark.parametrize("username,expected_status",
    [
        ("john_snow", 201),
        ("JOHN_SNOW", 201),
        ("johnsnow", 201),
        ("john_snow___", 201),
        ("_john_snow", 201),
        ("_john_snow_", 201),
        ("_____", 201),
        ("12345", 201),
        ("john-snow", 422),
        ("john_snow😭", 422),
        ("johnsnow*", 422),
        ("johnsnow//", 422),
        ("johnsnow\\", 422),
        ("john>snow", 422),
        ("john@snow", 422),
        ("john snow", 422),
        (" john snow", 422),
        # longer than 19 characters
        ("123456789101112131415", 422),
        ("", 422),
        ("😭👋🏾🤢", 422),

    ]
)
def test_username_is_valid(client, username, expected_status):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "azor_ahi@starkentaprise.wstro",
            "password": "Dany",
            "username": username
        })

    assert resp.status_code == expected_status


def test_create_invite_returns_201(client, login):
    resp = client.post("/api/v1/auth/invite")

    assert resp.status_code == 201


def test_create_invite_requires_login(client):
    resp = client.post("/api/v1/auth/invite")

    assert resp.status_code == 401
    assert resp.json["message"] == "Login required for this action"


def test_create_invite_returns_relative_join_path(client, login):
    resp = client.post("/api/v1/auth/invite")

    assert resp.status_code == 201
    assert resp.json["join_url"].startswith("join/")
    assert not resp.json["join_url"].startswith("http")


def test_create_invite_persists_invite(session, client, login):
    resp = client.post("/api/v1/auth/invite")
    assert resp.status_code == 201

    _, invite = _invite_from_join_url(session, resp.json["join_url"])
    assert invite is not None


def test_create_invite_stores_hashed_token(session, client, login):
    resp = client.post("/api/v1/auth/invite")
    assert resp.status_code == 201

    token, invite = _invite_from_join_url(session, resp.json["join_url"])
    assert invite.token_hash == secure.hash_invite_token(token)


def test_create_invite_sets_creator(session, client, login):
    resp = client.post("/api/v1/auth/invite")
    assert resp.status_code == 201

    _, invite = _invite_from_join_url(session, resp.json["join_url"])
    user_deets = single_user()
    creator = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == user_deets["username"])
        .one()
    )
    assert invite.created_by_user_id == creator.uuid


def test_create_invite_sets_default_expiry(session, client, login):
    resp = client.post("/api/v1/auth/invite")
    assert resp.status_code == 201

    _, invite = _invite_from_join_url(session, resp.json["join_url"])
    delta = invite.expires_at - invite.date_created
    assert timedelta(days=3) - timedelta(seconds=5) <= delta
    assert delta <= timedelta(days=3) + timedelta(seconds=5)


def test_create_invite_does_not_store_plaintext_token(session, client, login):
    resp = client.post("/api/v1/auth/invite")
    assert resp.status_code == 201

    token, invite = _invite_from_join_url(session, resp.json["join_url"])
    assert invite.token_hash != token
    assert token not in invite.token_hash


def test_create_invite_can_create_multiple_invites_for_same_user(
    session,
    client,
    login,
):
    first_resp = client.post("/api/v1/auth/invite")
    assert first_resp.status_code == 201

    second_resp = client.post("/api/v1/auth/invite")
    assert second_resp.status_code == 201

    assert first_resp.json["join_url"] != second_resp.json["join_url"]

    first_token, first_invite = _invite_from_join_url(
        session,
        first_resp.json["join_url"],
    )
    second_token, second_invite = _invite_from_join_url(
        session,
        second_resp.json["join_url"],
    )

    assert first_token != second_token
    assert first_invite.uuid != second_invite.uuid
    assert first_invite.created_by_user_id == second_invite.created_by_user_id


def test_create_invite_returns_500_when_invite_creation_fails(
    mocker,
    client,
    login,
):
    mocker.patch(
        "corna.controls.auth_control.create_invite",
        side_effect=auth_control.InviteCreationError("Failed to create invite"),
    )

    resp = client.post("/api/v1/auth/invite")

    assert resp.status_code == 500
    assert resp.json["message"] == "Failed to create invite"


def test_invite_request__create(client, session):
    response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "GoJo6eyes@aurafarm.com",
            "referral_source": " Limitless ",
        },
    )

    assert response.status_code == 201

    invite_request = (
        session
        .query(models.InviteRequestTable)
        .filter_by(email_address="gojo6eyes@aurafarm.com")
        .one()
    )

    assert invite_request.referral_source == "Limitless"
    assert invite_request.status == models.InviteRequestStatus.PENDING


def test_invite_request__duplicate_pending_request_is_ignored(client, session):
    first_response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "gojo6eyes@aurafarm.com",
        },
    )

    second_response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "GoJo6eyes@aurafarm.com",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code in {201, 202}

    requests = (
        session
        .query(models.InviteRequestTable)
        .filter_by(email_address="gojo6eyes@aurafarm.com")
        .all()
    )

    assert len(requests) == 1
    assert requests[0].status == models.InviteRequestStatus.PENDING


def test_invite_request__already_invited_request_is_ignored(
    client,
    session,
):
    # this is the user who will "invite" in this test but also joinbot is
    # the root of system invite requests
    system_user = (
        session
        .query(models.UserTable)
        .filter_by(username="joinbot")
        .one()
    )

    previous = models.InviteRequestTable(
        uuid=utils.get_uuid(),
        email_address="frieren@aurafarm.com",
        status=models.InviteRequestStatus.INVITED,
        reviewed_at=get_utc_now(),
        invited_at=get_utc_now(),
    )

    invite = models.InviteTable(
        uuid=utils.get_uuid(),
        token_hash="test-token-hash",
        created_by_user_id=system_user.uuid,
        date_created=get_utc_now(),
        expires_at=get_utc_now() + timedelta(days=3),
    )

    session.add(invite)
    session.flush()

    previous.invite_id = invite.uuid

    session.add(previous)
    session.commit()

    response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "frieren@aurafarm.com",
        },
    )

    assert response.status_code in {201, 202}

    requests = (
        session
        .query(models.InviteRequestTable)
        .filter_by(email_address="frieren@aurafarm.com")
        .all()
    )

    assert len(requests) == 1
    assert requests[0].status == models.InviteRequestStatus.INVITED


def test_invite_request__email_already_in_use_is_ignored(
    client,
    session,
    user,
):
    response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "azor_ahi@starkentaprise.wstro",
        },
    )

    assert response.status_code in {201, 202}

    invite_request = (
        session
        .query(models.InviteRequestTable)
        .filter_by(
            email_address="azor_ahi@starkentaprise.wstro",
        )
        .one_or_none()
    )

    assert invite_request is None


def test_invite_request__new_request_allowed_after_rejection(client, session):
    previous = models.InviteRequestTable(
        uuid=utils.get_uuid(),
        email_address="frieren@aurafarm.com",
        status=models.InviteRequestStatus.REJECTED,
        reviewed_at=get_utc_now(),
    )

    session.add(previous)
    session.commit()

    response = client.post(
        "/api/v1/auth/invite-request",
        json={
            "email": "frieren@aurafarm.com",
        },
    )

    assert response.status_code == 201

    requests = (
        session
        .query(models.InviteRequestTable)
        .filter_by(email_address="frieren@aurafarm.com")
        .order_by(models.InviteRequestTable.date_created)
        .all()
    )

    assert len(requests) == 2
    assert requests[0].status == models.InviteRequestStatus.REJECTED
    assert requests[1].status == models.InviteRequestStatus.PENDING
    assert requests[1].uuid != requests[0].uuid


"""
Regression test.

Uses two independent database sessions and concurrent requests to ensure
that a single-use invite cannot be redeemed more than once. The exact
thread scheduling is nondeterministic, but the observable behaviour must
always be:
    - one successful registration
    - one InvalidInviteError
    - one user created
"""
def test_invite_cannot_be_redeemed_twice(session_class):
    """Only one concurrent request can redeem a single-use invite."""
    from concurrent.futures import ThreadPoolExecutor
    from http import HTTPStatus
    from threading import Barrier
    
    from greenlet import getcurrent
    from sqlalchemy.orm import scoped_session

    from corna.app import create_app
    from corna.controls import auth_control
    from corna.utils import get_utc_now, utils

    setup_session = session_class()

    user_uuid = utils.get_uuid()
    # the boostrap context does not get created until the `register` function
    # below gets called so there are no system users at the time that we try
    # to create the invite. This is a simple workaround as the main thing we're
    # trying to test is how we handle race conditions
    system_user = models.UserTable(
        uuid=user_uuid,
        username="system",
        number=0,
        date_created=get_utc_now(),
        is_system_account=True,
    )

    setup_session.add(system_user)
    setup_session.flush()

    invite_token = auth_control.create_invite_for_user(
        setup_session,
        user_uuid,
    )

    setup_session.commit()


    first_user = single_user()
    second_user = single_user()
    second_user["email"] = "second@example.com"
    second_user["username"] = "second_user"

    first_user["token"] = invite_token
    second_user["token"] = invite_token

    # Both workers reach the request at approximately the same time.
    barrier = Barrier(2)

    def register(user_deets):
        request_session = scoped_session(
            session_class,
            scopefunc=getcurrent,
        )

        app = create_app(request_session)
        app.config["TESTING"] = True
        client = app.test_client()

        try:
            barrier.wait()

            response = client.post(
                "/api/v1/auth/register",
                json=user_deets,
            )

            if response.status_code == 400:
                assert response.json["message"] == \
                    "Invite token is invalid or expired."

            return response.status_code
        finally:
            request_session.remove()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(register, first_user),
            executor.submit(register, second_user),
        ]

        status_codes = [
            future.result()
            for future in futures
        ]

    assert sorted(status_codes) == sorted([
        HTTPStatus.CREATED,
        HTTPStatus.BAD_REQUEST,
    ])

    verification_session = session_class()

    try:
        assert (
            verification_session
            .query(models.EmailTable)
            .count()
        ) == 1

        assert (
            verification_session
            .query(models.UserTable)
            .filter(models.UserTable.is_system_account.is_(False))
            .count()
        ) == 1

        invite = (
            verification_session
            .query(models.InviteTable)
            .filter(
                models.InviteTable.token_hash
                == secure.hash_invite_token(invite_token)
            )
            .one()
        )

        assert invite.redeemed_at is not None
        assert invite.redeemed_by_user_id is not None

        registered_usernames = {
            username
            for username, in (
                verification_session
                .query(models.UserTable.username)
                .filter(
                    models.UserTable.username.in_([
                        first_user["username"],
                        second_user["username"],
                    ])
                )
                .all()
            )
        }

        assert len(registered_usernames) == 1
    finally:
        verification_session.close()
