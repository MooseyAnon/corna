import pytest

from corna.db import models
from corna.middleware import permissions as perms
from corna.utils import get_utc_now, utils
from tests import shared_data as shared


def many_users_helper(session, number=50):

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


def test_create_role__default_perms(client, session, corna):
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "New Role",
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 201

    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # get user to enusre correct account created role
    user = session.query(models.UserTable).first()

    assert role.name == "new role"
    assert role.creator_uuid == user.uuid
    assert role.permissions == 449  # default role

    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected


def test_create_role__perm_does_not_exist(client, session, corna):
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "New Role",
            # default permissions
            "permissions": ["read", "comment", "like", "I do not exist"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 201

    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # get user to enusre correct account created role
    user = session.query(models.UserTable).first()

    assert role.name == "new role"
    assert role.creator_uuid == user.uuid
    assert role.permissions == 193

    # check all permissions are correct
    expected = {
        "change_theme": False,
        "comment": True,
        "delete": False,
        "edit": False,
        "follow": False,
        "like": True,
        "read": True,
        "change_permissions": False,
        "write": False,
    }

    assert perms.perms(role.permissions) == expected


def test_create_role__duplicate_names(client, session, corna):
    # create role
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "I am a duplicate",
            "permissions": [],
            "domain_name": shared.corna_info["domain_name"],
        }
    )

    assert resp.status_code == 201
    assert session.query(models.Role).count() == 1

    # try make role with same name again
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "I am a duplicate",
            "permissions": [],
            "domain_name": shared.corna_info["domain_name"],
        }
    )

    assert resp.status_code == 400
    assert resp.json["message"] == "Duplicate roles are not permitted"
    # make sure nothing was saved
    assert session.query(models.Role).count() == 1


def test_create_role__corna_does_not_exist(client, session, login):
    # create role
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "I am a duplicate",
            "permissions": [],
            "domain_name": shared.corna_info["domain_name"],
        }
    )

    assert resp.status_code == 400
    assert resp.json["message"] == "Corna does not exist"
    assert session.query(models.Role).count() == 0


def test_create_role__banned_role(client, session, corna):
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "Banned",
            "permissions": [],
            "domain_name": shared.corna_info["domain_name"],
        }
    )
    assert resp.status_code == 201

    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # get user to enusre correct account created role
    user = session.query(models.UserTable).first()

    assert role.name == "banned"
    assert role.creator_uuid == user.uuid
    assert role.permissions == 0


    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected


def test_create_role__missing_name(client, session):
    resp = client.post("/api/v1/roles", json={"permissions": []})
    assert resp.status_code == 422
    assert session.query(models.Role).count() == 0


def test_create_role__missing_perms(client, session):
    resp = client.post("/api/v1/roles", json={"name": "Should not work"})
    assert resp.status_code == 422
    assert session.query(models.Role).count() == 0


def test_update_role__add_write_to_default_role(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected

    # update role
    resp = client.put(
        "/api/v1/roles",
        json={
            "name": "default",
            "permissions": ["read", "comment", "like", "follow", "write"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 204

    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()

    # check all permissions are correct
    expected = {
        "change_theme": False,
        "comment": True,
        "delete": False,
        "edit": False,
        "follow": True,
        "like": True,
        "read": True,
        "change_permissions": False,
        "write": True,
    }

    assert perms.perms(role.permissions) == expected


def test_update_role__perm_does_not_exist(client, session, corna):
     # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected

    # update role
    resp = client.put(
        "/api/v1/roles",
        json={
            "name": "default",
            "permissions": ["read", "comment", "like", "follow", "doesn't exist"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 204

    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()

    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected


def test_update_role__corna_role_does_not_exist(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1
    role = session.query(models.Role).first()

    # check all permissions are correct
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

    assert perms.perms(role.permissions) == expected

    # update no existent role
    resp = client.put(
        "/api/v1/roles",
        json={
            "name": "I do not exist",
            "permissions": ["read", "comment", "like", "follow", "write"],
            "domain_name": shared.corna_info["domain_name"],
        })

    assert resp.status_code == 400
    assert resp.json["message"] == "Role not found"

    # ensure perms are the same
    assert session.query(models.Role).count() == 1
    new_role = (
        session
        .query(models.Role)
        .filter(models.Role.name == "default")
        .first()
    )

    assert new_role != role
    assert perms.perms(new_role.permissions) == expected


def test_delete_role(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.delete(
        "/api/v1/roles",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
        })

    assert resp.status_code == 204
    assert session.query(models.Role).count() == 0


def test_delete_role__role_does_not_exist(client, session, corna):
    # ensure we have nothing saved
    assert session.query(models.Role).count() == 0
    # delete a role that does not exist
    resp = client.delete(
        "/api/v1/roles",
        json={
            "name": "I dont exist",
            "domain_name": shared.corna_info["domain_name"],
        })

    assert resp.status_code == 204
    assert session.query(models.Role).count() == 0


def test_add_perm(client, session, corna):

    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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
    assert perms.perms(role.permissions) == expected

    # add perm to role
    resp = client.put(
        "/api/v1/roles/permissions/add",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "write",
        })

    assert resp.status_code == 204
    # make sure we have not saved anything new
    assert session.query(models.Role).count() == 1
    role = session.query(models.Role).first()
    # check all permissions are correct
    expected = {
        "change_theme": False,
        "comment": True,
        "delete": False,
        "edit": False,
        "follow": True,
        "like": True,
        "read": True,
        "change_permissions": False,
        "write": True,
    }
    assert perms.perms(role.permissions) == expected


def test_add_perm__add_same_perm(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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
    assert perms.perms(role.permissions) == expected

    # add same perm to role
    resp = client.put(
        "/api/v1/roles/permissions/add",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "comment",
        })

    assert resp.status_code == 204
    # make sure we have not saved anything new
    assert session.query(models.Role).count() == 1
    new_role = session.query(models.Role).first()
    # check all permissions are correct
    assert role != new_role
    assert perms.perms(new_role.permissions) == expected


def test_add_perm__role_does_not_exist(client, session, corna):
    assert session.query(models.Role).count() == 0
    # add same perm to role
    resp = client.put(
        "/api/v1/roles/permissions/add",
        json={
            "name": "I dont exist",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "comment",
        })

    assert resp.status_code == 400
    assert session.query(models.Role).count() == 0


def test_add_perm__perm_does_not_exist(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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
    assert perms.perms(role.permissions) == expected

    # add perm that doesn't exist
    resp = client.put(
        "/api/v1/roles/permissions/add",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "commen",
        })

    assert resp.status_code == 204
    # make sure we have not saved anything new
    assert session.query(models.Role).count() == 1
    new_role = session.query(models.Role).first()
    # check all permissions are correct
    assert role != new_role
    assert perms.perms(new_role.permissions) == expected


def test_remove_perm(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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
    assert perms.perms(role.permissions) == expected

    # add perm to role
    resp = client.put(
        "/api/v1/roles/permissions/remove",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "comment",
        })

    assert resp.status_code == 204
    # make sure we have not saved anything new
    assert session.query(models.Role).count() == 1
    role = session.query(models.Role).first()
    # check all permissions are correct
    expected = {
        "change_theme": False,
        "comment": False,
        "delete": False,
        "edit": False,
        "follow": True,
        "like": True,
        "read": True,
        "change_permissions": False,
        "write": False,
    }
    assert perms.perms(role.permissions) == expected


def test_remove_perm__perm_does_not_exist(client, session, corna):
     # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    role = session.query(models.Role).first()
    # check all permissions are correct
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
    assert perms.perms(role.permissions) == expected

    # add perm to role
    resp = client.put(
        "/api/v1/roles/permissions/remove",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "I dont exist",
        })

    assert resp.status_code == 204
    # make sure we have not saved anything new
    assert session.query(models.Role).count() == 1
    role = session.query(models.Role).first()
    assert perms.perms(role.permissions) == expected


def test_remove_perm__role_does_not_exist(client, session, corna):
    assert session.query(models.Role).count() == 0

    # add perm to role
    resp = client.put(
        "/api/v1/roles/permissions/remove",
        json={
            "name": "I dont exist",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "comment",
        })
    assert resp.status_code == 400
    assert resp.json["message"] == "Role not found"


def test_give_role__give_user_role(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .first()
    )

    assert len(user.roles) == 1

    maps = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user.uuid)
        .all()
    )
    assert len(maps) == 1


def test_give_role__role_to_none_owner(client, session, corna):
    many_users_helper(session, number=1)
    assert session.query(models.UserTable).count() == 2
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })

    assert resp.status_code == 201

    # ensure correct user has role
    user1 = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .first()
    )

    user2 = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow_1")
        .first()
    )

    assert len(user1.roles) == 0
    assert len(user2.roles) == 1

    maps1 = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user1.uuid)
        .all()
    )

    maps2 = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user2.uuid)
        .all()
    )

    assert len(maps1) == 0
    assert len(maps2) == 1


def test_give_role__user_already_has_role(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201

    # give user same role again
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .first()
    )

    assert len(user.roles) == 1

    maps = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user.uuid)
        .all()
    )
    assert len(maps) == 1


def test_give_role__othe_user_does_not_exist(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    fake_user_name = "i-dont-exist"
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": fake_user_name,
        })

    assert resp.status_code == 400
    assert resp.json["message"] == \
        f"User with username {fake_user_name} does not exist"


def test_give_role__role_does_not_exist(client, corna):
    fake_role_name = "i-dont-exist"
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": fake_role_name,
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 400
    assert resp.json["message"] == f"Role named {fake_role_name} not found"


def test_take_role__take_user_role(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # give user role
    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .first()
    )

    assert len(user.roles) == 1

    # take user role ---------->
    resp = client.post(
        "/api/v1/roles/take",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow")
        .first()
    )

    assert len(user.roles) == 0

    maps = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user.uuid)
        .all()
    )
    assert len(maps) == 0


def test_take_role__none_owner_user(client, session, corna):
    many_users_helper(session, number=1)
    assert session.query(models.UserTable).count() == 2
    assert session.query(models.role_user_map).count() == 0
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })

    assert resp.status_code == 201

    # take user role ---------->
    resp = client.post(
        "/api/v1/roles/take",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })

    assert resp.status_code == 201

    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow_1")
        .first()
    )

    assert len(user.roles) == 0

    maps = (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user.uuid)
        .all()
    )
    assert len(maps) == 0


def test_take_role__other_user_does_not_exist(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # take take role from user who deosn't exist
    resp = client.post(
        "/api/v1/roles/take",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201


def test_take_role__role_does_not_exist(client, corna):
    fake_role_name = "i-dont-exist"
    resp = client.post(
        "/api/v1/roles/take",
        json={
            "name": fake_role_name,
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow",
        })

    assert resp.status_code == 201


def test_perm_list(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # get perm list
    dom_name = shared.corna_info["domain_name"]
    role_name = "default"
    resp = client.get(f"/api/v1/roles/{dom_name}/{role_name}/permissions")
    assert resp.status_code == 200

    expected = {
        "corna": shared.corna_info["domain_name"],
        "name": "default",
        "permissions": ["read", "comment", "like", "follow"]
    }
    assert resp.json == expected


def test_perm_list__role_does_not_exist(client, corna):
    dom_name = shared.corna_info["domain_name"]
    role_name = "default"
    # get perm list
    resp = client.get(f"/api/v1/roles/{dom_name}/{role_name}/permissions")
    assert resp.status_code == 400


def test_perm_list__corna_does_not_exist(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    dom_name = shared.corna_info["domain_name"]
    role_name = "fake-perm"
    # get perm list
    resp = client.get(f"/api/v1/roles/{dom_name}/{role_name}/permissions")
    assert resp.status_code == 400


def test_user_list(client, session, corna):
    # make loads of users
    many_users_helper(session)

    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # give a bunch of users role the role
    for i in range(1, 21):
        username = f"john_snow_{i}"
        resp = client.post(
            "/api/v1/roles/give",
            json={
                "name": "default",
                "domain_name": shared.corna_info["domain_name"],
                "username": username,
            })

        assert resp.status_code == 201

    # pick a random user and check if they have the role
    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == "john_snow_5")
        .first()
    )

    assert len(user.roles) == 1

    dom_name = shared.corna_info["domain_name"]
    role_name = "default"
    # check user list
    resp = client.get(f"/api/v1/roles/{dom_name}/{role_name}/users")
    assert resp.status_code == 200

    expected = {
        "corna": shared.corna_info["domain_name"],
        "name": "default",
        "users" : [
            "john_snow_1",
            "john_snow_2",
            "john_snow_3",
            "john_snow_4",
            "john_snow_5",
            "john_snow_6",
            "john_snow_7",
            "john_snow_8",
            "john_snow_9",
            "john_snow_10",
            "john_snow_11",
            "john_snow_12",
            "john_snow_13",
            "john_snow_14",
            "john_snow_15",
            "john_snow_16",
            "john_snow_17",
            "john_snow_18",
            "john_snow_19",
            "john_snow_20",
        ],
    }

    assert resp.json == expected


def test_user_list__role_does_not_exist(client, corna):
    dom_name = shared.corna_info["domain_name"]
    role_name = "fake-role"
    # check user list
    resp = client.get(f"/api/v1/roles/{dom_name}/{role_name}/users")
    assert resp.status_code == 200

    expected = expected = {
        "corna": shared.corna_info["domain_name"],
        "name": "fake-role",
        "users" : [],
    }
    assert resp.json == expected


def test_user_role_list(client, session, corna):
    # make a bunch of roles
    for i in range(9):
        create_role_helper(
            client,
            name=f"default_{i}",
            permissions=["read", "comment", "like", "follow"],
        )

        # dont give every role
        if i % 2 == 0:
            resp = client.post(
                "/api/v1/roles/give",
                json={
                    "name": f"default_{i}",
                    "domain_name": shared.corna_info["domain_name"],
                    "username": "john_snow",
                })

            assert resp.status_code == 201

    domain_name = shared.corna_info["domain_name"]
    resp = client.get(f"/api/v1/roles/{domain_name}/john_snow")
    assert resp.status_code == 200

    expected = {
        "username": "john_snow",
        "corna": shared.corna_info["domain_name"],
        "roles": [
            "default_0",
            "default_2",
            "default_4",
            "default_6",
            "default_8",
        ],
    }

    assert resp.json == expected


def test_user_role_list__no_roles(client, corna):
    domain_name = shared.corna_info["domain_name"]
    resp = client.get(f"/api/v1/roles/{domain_name}/john_snow")
    assert resp.status_code == 200

    expected = {
        "username": "john_snow",
        "corna": shared.corna_info["domain_name"],
        "roles": [],
    }

    assert resp.json == expected


def test_user_role_list__corna_doesn_not_exist(client, login):
    domain_name = "i-dont-exist"
    resp = client.get(f"/api/v1/roles/{domain_name}/john_snow")
    assert resp.status_code == 200

    expected = {
        "username": "john_snow",
        "corna": domain_name,
        "roles": [],
    }

    assert resp.json == expected


def test_user_perm_list(client, session, corna):
    # make loads of users
    many_users_helper(session)

    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    # give a bunch of users role the role
    for i in range(30, 42):
        username = f"john_snow_{i}"
        resp = client.post(
            "/api/v1/roles/give",
            json={
                "name": "default",
                "domain_name": shared.corna_info["domain_name"],
                "username": username,
            })

        assert resp.status_code == 201

    domain_name = shared.corna_info["domain_name"]
    perm = "read"
    resp = client.get(f"/api/v1/roles/{domain_name}/users/{perm}")
    assert resp.status_code == 200

    expected = {
        "corna": shared.corna_info["domain_name"],
        "permission": "read",
        "users": [
            "john_snow_30",
            "john_snow_31",
            "john_snow_32",
            "john_snow_33",
            "john_snow_34",
            "john_snow_35",
            "john_snow_36",
            "john_snow_37",
            "john_snow_38",
            "john_snow_39",
            "john_snow_40",
            "john_snow_41",
        ]
    }

    assert resp.json["permission"] == expected["permission"]
    assert len(resp.json["users"]) == len(expected["users"])
    # lists are unstable i.e. the order can change so we make it a set
    assert set(resp.json["users"]) == set(expected["users"])

# ----------- test permissions i.e. is user allowed to interact with roles

def test_create_role__user_is_not_allowed(client, session, corna):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # create role on another users corna
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "New Role",
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not create a role"


def test_update_role__user_is_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # update role
    resp = client.put(
        "/api/v1/roles",
        json={
            "name": "default",
            "permissions": ["read", "comment", "like", "follow", "write"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not update a role"


def test_delete_role__user_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # update role
    resp = client.delete(
        "/api/v1/roles",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not delete a role"


def test_add_perm__user_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    # update role
    resp = client.put(
        "/api/v1/roles/permissions/add",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "write",
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not add permission to role"


def test_remove_perm__user_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    resp = client.put(
        "/api/v1/roles/permissions/remove",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "permission": "comment",
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not remove permission from role"


def test_give_role__user_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/roles/give",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not give a role"


def test_take_role__user_not_allowed(client, session, corna):
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "comment", "like", "follow"],
    )
    # check db saved correctly
    assert session.query(models.Role).count() == 1

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # create another user
    many_users_helper(session, number=1)
    # login a new user
    resp = client.post("/api/v1/auth/login", json={
            "email": "azor_ahi_1@starkentaprise.wstro",
            "password": "Dany",
        }
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/roles/take",
        json={
            "name": "default",
            "domain_name": shared.corna_info["domain_name"],
            "username": "john_snow_1",
        })
    assert resp.status_code == 401
    assert resp.json["message"] == "User can not take a role"


def test_create_role__user_has_role(client, session, corna):
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

    # create new role on main users corna
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "New Role",
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 201
    # check db saved correctly
    assert session.query(models.Role).count() == 2


def test_create_role__user_has_role_but_invalid(client, session, corna):
    # create another user
    many_users_helper(session, number=1)
    # create default role
    create_role_helper(
        client,
        name="default",
        permissions=["read", "write"],
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

    # create new role on main users corna
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": "New Role",
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == 401
    # check db saved correctly
    assert session.query(models.Role).count() == 1


@pytest.mark.parametrize("name,expected_status",
    [
        ("New Role", 201),
        ("😀😭🤢", 201),
        ("a" * 40, 201),
        ("a" * 41, 422),
        ("", 422),
        ("        ", 422),
    ]
)
def test_create_role__valid_role_name(client, corna, name, expected_status):
    resp = client.post(
        "/api/v1/roles",
        json={
            "name": name,
            # default permissions
            "permissions": ["read", "comment", "like", "follow"],
            "domain_name": shared.corna_info["domain_name"],
        })
    assert resp.status_code == expected_status
