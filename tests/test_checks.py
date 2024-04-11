"""Test checks."""

import pytest

from corna.db import models
from corna.middleware import check
from corna.middleware import permissions as perms
from corna.utils import get_utc_now, utils
from tests import shared_data as shared


def _corna_with_perms_helper(client, permissions=[]):
    """Create a Corna with permissions."""
    resp = client.post(
        f"/api/v1/corna/{shared.corna_info['domain_name']}",
        json={
            "title": shared.corna_info["title"],
            # for a private Corna, permissions field should not be missing
            # but posted with an empty list
            "permissions": permissions,
        },
    )
    assert resp.status_code == 201


def _create_role_helper(client, name="fake role", permissions=[]):
    """Create a new role."""
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": name,
            "permissions": permissions,
            "domain_name": shared.corna_info["domain_name"],
        }
    )
    assert resp.status_code == 201


def _create_user_helper(session, email, username):

    user = {
        "email_address": email,
        "password": "Dany",
        "user_name": username,
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
        )
    )

    session.commit()
    assert session.query(models.UserTable).count() > 1


def _give_user_role_helper(client, role, user):

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": role,
            "domain_name": shared.corna_info["domain_name"],
            "username": user,
        })

    assert resp.status_code == 201


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], False),
        (["read"], True),
        (["write", "follow", "like"], False),
        (["read", "write", "edit"], True),
    ]
)
def test_can_read__private_corna(client, session, login, perm_list, expected):
    # create none owner user
    _create_user_helper(session, "bran@builder.wntrfll", "builder_bran")

    # make a private Corna
    _corna_with_perms_helper(client)

    # create reader role
    _create_role_helper(client, name="default", permissions=perm_list)

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "builder_bran",
        })

    assert resp.status_code == 201

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "bran@builder.wntrfll",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    assert check.can_read(
        session,
        shared.corna_info["domain_name"],
        "builder_bran",
    ) == expected


def test_is_owner__true(session, corna):

    assert check.is_owner(
        session,
        shared.corna_info["domain_name"],
        "john_snow",
    ) == True
    # assert False


def test_is_owner__false(client, session, corna):

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # create none owner user
    _create_user_helper(session, "bran@builder.wntrfll", "builder_bran")

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "bran@builder.wntrfll",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create corna for fake user
    resp = client.post(
        f"/api/v1/corna/bran-the-builder",
        json={
            "title": "building shit in my wheelchair",
            "permissions": [],
        },
    )
    assert resp.status_code == 201
    
    assert check.is_owner(
        session,
        shared.corna_info["domain_name"],
        "builder_bran",
    ) == False


def test_can_write__corna_owner(client, session, login):
    # make a private Corna
    _corna_with_perms_helper(client)

    assert check.can_write(
        session,
        shared.corna_info["domain_name"],
        "john_snow",
    ) == True


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], False),
        (["read"], False),
        (["edit"], False),
        (["write"], True),
        (["write", "follow", "like"], True),
        (["read", "write", "edit"], True),
    ]
)
def test_can_write__not_owner(client, session, login, perm_list, expected):
    # make a private Corna
    _corna_with_perms_helper(client)

    # create reader role
    _create_role_helper(client, name="default", permissions=perm_list)

    # create none owner user
    _create_user_helper(session, "fake@user.com", "fake_user")

    # give user role
    _give_user_role_helper(client, "default",  "fake_user")

    # run test
    assert check.can_write(
        session,
        shared.corna_info["domain_name"],
        "fake_user",
    ) == expected


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], False),
        (["read"], False),
        (["edit"], False),
        (["write"], True),
        (["write", "follow", "like"], True),
        (["read", "write", "edit"], True),
    ]
)
def test_can_write__loose_corna_perms(
    client, session, login, perm_list, expected
):

     # make a Corna
    _corna_with_perms_helper(client, permissions=perm_list)

    # create none owner user
    _create_user_helper(session, "fake@user.com", "fake_user")

    # run test
    assert check.can_write(
        session,
        shared.corna_info["domain_name"],
        "fake_user",
    ) == expected


def test_can_write__user_is_banned(client, session, login):
    """This is to ensure that we dont allow banned users to have access to
    write (or do anything else).
    There is a potential bug where a user has a 0 role, which is essentially
    'banned', but because that is a valid role, and our role checking code
    looks for at least one role with a matching value, a banned user maybe able
    to read a private page or do an action they have no permission doing.

    To reproduce this bug, put 0 as the perm directly into _user_has_perm, it
    always returns True.
    """
    # create none owner user
    _create_user_helper(session, "bran@builder.wntrfll", "builder_bran")

    # make a private Corna
    _corna_with_perms_helper(client)

    # create banned role
    _create_role_helper(client, name="default")

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "builder_bran",
        })

    assert resp.status_code == 201

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "bran@builder.wntrfll",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create corna for fake user
    # resp = client.post(
    #     f"/api/v1/corna/bran-the-builder",
    #     json={
    #         "title": "building shit in my wheelchair",
    #         "permissions": [],
    #     },
    # )
    # assert resp.status_code == 201

    assert check.can_write(
        session,
        shared.corna_info["domain_name"],
        "builder_bran",
    ) == False


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], False),
        (["change_permissions"], True),
        (["write", "follow", "like"], False),
        (["change_permissions", "write", "edit"], True),
    ]
)
def test_can_change_permissions__not_owner(
    client, session, login, perm_list, expected
):

    # create none owner user
    _create_user_helper(session, "bran@builder.wntrfll", "builder_bran")

    # make a private Corna
    _corna_with_perms_helper(client)

    # create reader role
    _create_role_helper(client, name="default", permissions=perm_list)

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "builder_bran",
        })

    assert resp.status_code == 201

    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "bran@builder.wntrfll",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    assert check.can_change_permissions(
        session,
        shared.corna_info["domain_name"],
        "builder_bran",
    ) == expected


def test_can_change_permissions__is_owner(session, corna):

    assert check.can_change_permissions(
        session,
        shared.corna_info["domain_name"],
        "john_snow",
    ) == True


@pytest.mark.parametrize("perm_list,expected",
    [
        ([], False),
        (["read"], False),
        (["edit"], False),
        (["change_permissions"], True),
        (["change_permissions", "follow", "like"], True),
        (["read", "change_permissions", "edit"], True),
    ]
)
def test_can_change_permissions__loose_perms(
    client, session, login, perm_list, expected
):
     # make a Corna
    _corna_with_perms_helper(client, permissions=perm_list)

    # create none owner user
    _create_user_helper(session, "fake@user.com", "fake_user")

    # run test
    assert check.can_change_permissions(
        session,
        shared.corna_info["domain_name"],
        "fake_user",
    ) == expected


@pytest.mark.parametrize("function,perm_list,expected",
    [
        (check.can_read, [], False),
        (check.can_write, [], False),
        (check.can_change_permissions, [], False),
        (check.can_read, ["read"], False),
        (check.can_write, ["write"], False),
        (check.can_change_permissions, ["change_permissions"], False),
    ]
)
def test_permissions_leaks(
    client, session, login, function, perm_list, expected
):
    """Ensure that just because a user has a role with a certain permission
    e.g. 'write' for some random Corna, they do not have that permission on
    Corna's they are not supposed to. This was a bug caught during development.
    """
    # make a private Corna
    _corna_with_perms_helper(client)
    # logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # create none owner user
    _create_user_helper(session, "bran@builder.wntrfll", "builder_bran")

    # login as new fake user
    resp = client.post("/api/v1/auth/login", json={
            "email": "bran@builder.wntrfll",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create corna for fake user
    resp = client.post(
        f"/api/v1/corna/bran-the-builder",
        json={
            "title": "building shit in my wheelchair",
            "permissions": [],
        },
    )
    assert resp.status_code == 201

    # create reader role for `fake-user-domain`
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "builder-default",
            "permissions": perm_list,
            "domain_name": "bran-the-builder",
        }
    )
    assert resp.status_code == 201

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "builder-default",
            "domain_name": "bran-the-builder",
            "username": "builder_bran",
        })

    assert resp.status_code == 201

    # run test
    assert function(
        session,
        shared.corna_info["domain_name"],
        "builder_bran",
    ) == expected
