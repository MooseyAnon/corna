import pytest

from corna.db import models
from corna.utils import get_utc_now, utils
from tests import shared_data as shared


def ordered(obj):
    """Orders a list of dicts to make them comparable.

    source: https://stackoverflow.com/a/25851972
    """
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def upload_avatar(session):
    """Upload a fake avatar for testing."""

    fake_uuid = "00000000-0000-0000-0000-000000000000"
    session.add(
        models.Media(
            uuid=fake_uuid,
            url_extension="abcdef",
            path="some/fake/path",
            size=8096,
            # fake timestamp from posts tests
            created="2023-04-29T03:21:34",
            orphaned=True,
        )
    )

    session.commit()
    return fake_uuid


def give_user_avatar(session, uuid):
    # this function exists so we dont mess around with conftests as they are
    # shared across all tests, any future changes to avatars or how we do them
    # may cause many unrelated tests to fail
    curr_user = session.query(models.UserTable).first()
    curr_user.avatar = uuid
    session.commit()


def many_users_helper(session, number=50):
    avatar_uuid = upload_avatar(session)

    for i in range(1, number + 1):
        user = {
            "email_address": f"azor_ahi_{i}@starkentaprise.wstro",
            "password": "Dany",
            "user_name": f"john_snow_{i}",
        }
        
        session.add(
            models.EmailTable(
                email_address=user["email_address"],
                password=user["password"],
            )
        )

        session.add(
            models.UserTable(
                uuid=utils.get_uuid(),
                email_address=user["email_address"],
                username=user["user_name"],
                date_created=get_utc_now(),
                avatar=avatar_uuid,
            )
        )

    session.commit()
    assert session.query(models.UserTable).count() == number + 1


def create_role_helper(client, name="fake role", permissions=[]):
    """Helper function used in non-create tests."""
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": name,
            "permissions": permissions,
            "domain_name": shared.corna_info["domain_name"],
        }
    )
    assert resp.status_code == 201


def test_get_user_details__logged_in(session, mocker, client, login):
    mocker.patch("random.uniform", return_value=10)
    # ensure user has avatar
    give_user_avatar(session, upload_avatar(session))
    fake_url_slug = "abcdef"

    resp = client.get("/api/v1/user")
    assert resp.status_code == 200

    expected = {
        "username": "john_snow",
        "cred": 10,
        "role": "adventurer",
        "avatar": f"https://api.mycorna.com/v1/media/download/{fake_url_slug}",
    }

    assert resp.json == expected


def test_get_user_details__logged_out(client):
    resp = client.get("/api/v1/user")
    assert resp.status_code == 401


def test_get_role_list__no_roles(client, login):
    resp = client.get("/api/v1/user/roles/created")
    assert resp.status_code == 200

    expected = {"roles": []}
    assert resp.json == expected


def test_get_role_list__role_on_single_corna(client, corna):
    create_role_helper(client, permissions=["read", "write"])

    resp = client.get("/api/v1/user/roles/created")
    assert resp.status_code == 200

    expected = {"roles": [
            {
                "domain_name": "some-fake-domain",
                "name": "fake role",
            }
        ]
    }
    assert resp.json == expected


def test_get_role_list__roles_on_multiple_cornas(client, session, corna):
     # create another user
    many_users_helper(session, number=1)
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["change_permissions"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # give other user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })
    assert resp.status_code == 201

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # make current user a corna
    resp = client.post(
        f"/api/v1/corna/corna-number-two",
        json={"title": "hello world!"},
    )
    assert resp.status_code == 201

    # create role on current users corna
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "new user corna role",
            "permissions": ["read", "write"],
            "domain_name": "corna-number-two",
        }
    )
    assert resp.status_code == 201

    # create new role on main users corna
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "role on other corna",
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 201

    # check db saved correctly
    assert session.query(models.Role).count() == 3

    # ----------- test starts here --------

    resp = client.get("/api/v1/user/roles/created")
    assert resp.status_code == 200

    expected = [
        {"domain_name": "some-fake-domain", "name": "role on other corna"},
        {"domain_name": "corna-number-two", "name": "new user corna role"},
    ]

    assert len(resp.json["roles"]) == len(expected)
    assert ordered(resp.json["roles"]) == ordered(expected)
