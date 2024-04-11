"""Manage roles."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm.query import Query
from sqlalchemy.orm.scoping import scoped_session as Session

from corna.db import models
from corna.middleware import alchemy, check, permissions as perms
from corna.utils import errors, get_utc_now, utils

logger = logging.getLogger(__name__)


class NoneExistingRoleError(ValueError):
    """Nine existing role.

    Raised when a role does not exit.
    """


class DuplicateRoleError(ValueError):
    """Duplicate role error.

    Raised when role already exists.
    """


def new(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
    permissions: List[str],
) -> None:
    """Create new role.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param List[str] permissions: list of role permissions

    :raises errors.UnauthorizedActionError: if user is not authorized to
        create a role
    :raises errors.CornaNotFoundError: if corna not found
    :raises DuplicateRoleError: if role is a duplicate
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    corna_uuid: Optional[str] = alchemy.corna_uuid(session, domain_name)

    if not corna_uuid:
        raise errors.CornaNotFoundError("Corna does not exist")

    # order is important here, we need to ensure that there is a corna
    # before checking permissions as the checkers will raise the same error
    # as above but the message will be confising i.e. it will be because
    # no corna exists but the message will say that the user cannot create
    # a role.
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError("User can not create a role")

    if alchemy.role_uuid(session, name, corna_uuid) is not None:
        raise DuplicateRoleError("Duplicate roles are not permitted")

    session.add(
        models.Role(  # type: ignore[call-arg]
            uuid=utils.get_uuid(),
            name=name.lower(),
            created=get_utc_now(),
            permissions=perms.create_role(permissions),
            creator_uuid=curr_user.uuid,
            corna_uuid=corna_uuid,
        )
    )


def update(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
    permissions: List[str],
) -> None:
    """Update the permissions on a role.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param List[str] permissions: list of role permissions

    :raises errors.UnauthorizedActionError: if user is not authorized to
        update a role
    :raises NoneExistingRoleError: if role not found
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError("User can not update a role")

    corna_uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Optional[models.Role] = alchemy.role(session, name, corna_uuid)

    if not role:
        raise NoneExistingRoleError("Role not found")
    # with update, we do a wholesale replacement of the role rather than append
    # the diff. this makes it easy to remove perms from a role.
    role.permissions = perms.create_role(permissions)
    logger.info(
        "Updated permissions for role named %s on corna %s",
        name, domain_name,
    )


def delete(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
) -> None:
    """Delete a role from a given Corna.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain

    :raises errors.UnauthorizedActionError: if user is not authorized to
        delete a role
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError("User can not delete a role")

    corna_uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Query = alchemy.role(session, name, corna_uuid, as_subquery=True)
    role.delete(synchronize_session=False)
    logger.info(
        "Deleted role named %s on Corna with domain name %s",
        name, domain_name
    )


def add(
    session: str,
    cookie: str,
    name: str,
    domain_name: str,
    permission: str,
) -> None:
    """Add permission to given a role.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param str permission: permission to add

    :raises errors.UnauthorizedActionError: if user is not authorized to
        add a permission to a role
    :raises NoneExistingRoleError: if role not found
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError(
            "User can not add permission to role")

    corna_uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Optional[models.Role] = alchemy.role(session, name, corna_uuid)

    if not role:
        logger.error("Role with named %s not found", name)
        raise NoneExistingRoleError("Role not found")

    role.permissions = perms.add_perm(role.permissions, permission)
    logger.info("Added the permission %s to role %s", permission, role.name)


def remove(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
    permission: str,
) -> None:
    """Remove a permission from a role.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param str permission: permission to remove

    :raises errors.UnauthorizedActionError: if user is not authorized to
        remove a permission from a role
    :raises NoneExistingRoleError: if role not found
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError(
            "User can not remove permission from role")

    uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Optional[models.Role] = alchemy.role(session, name, uuid)

    if not role:
        logger.error("Role with named %s not found", name)
        raise NoneExistingRoleError("Role not found")

    role.permissions = perms.remove_perm(role.permissions, permission)
    logger.info(
        "Removed the permission %s from role %s",
        permission, role.name,
    )


def give(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
    username: str,
) -> None:
    """Give a user a role.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param str username: user to give role to

    :raises errors.UnauthorizedActionError: if user is not authorized to
        give a role
    :raises errors.NoneExistingUserError: if user not found
    :raises NoneExistingRoleError: if role not found
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError("User can not give a role")

    user: Optional[models.UserTable] = alchemy.user(session, username)
    if not user:
        logger.error("Username %s not found", username)
        raise errors.NoneExistingUserError(
            f"User with username {username} does not exist")

    uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Optional[models.Role] = alchemy.role(session, name, uuid)

    if not role:
        logger.error("Role named %s not found", name)
        raise NoneExistingRoleError(f"Role named {name} not found")

    # give user role
    user.roles.append(role)

    logger.info("Added role %s to user %s", role.name, user.username)


def take(
    session: Session,
    cookie: str,
    name: str,
    domain_name: str,
    username: str,
) -> None:
    """Remove role from user.

    :param Session session: DB session
    :param str cookie: user cookie
    :param str name: role name
    :param str domain_name: Corna domain
    :param str username: user to give role to

    :raises errors.UnauthorizedActionError: if user is not authorized to
        take a role from a user
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    can_change_perm = check.can_change_permissions(
        session, domain_name, curr_user.username)

    if not can_change_perm:
        logger.warning(
            "Unauthorized role creation attempt by %s on corna %s",
            curr_user.username, domain_name
        )
        raise errors.UnauthorizedActionError("User can not take a role")

    user: Any = alchemy.user_uuid(session, username, as_subquery=True)
    uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    subquery: Any = alchemy.role_uuid(session, name, uuid, as_subquery=True)

    (
        session
        .query(models.role_user_map)
        .filter_by(user_id=user)
        .filter_by(role_id=subquery.scalar_subquery())
        .delete(synchronize_session=False)
    )

    logger.info("Attempted to remove role %s from user %s", name, username)


def permissions_list(
    session: Session,
    name: str,
    domain_name: str,
) -> List[str]:
    """List of permissions a role has.

    :param Session session: DB session
    :param str name: role name
    :param str domain_name: Corna domain

    :returns: list of permissions a role has
    :rtype: List[str]
    :raises NoneExistingRoleError: if role not found
    """
    uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role: Optional[models.Role] = alchemy.role(session, name, uuid)

    if not role:
        raise NoneExistingRoleError(
            f"No role named {name} on Corna {domain_name}")

    permissions_map: Dict[str, bool] = perms.perms(role.permissions)

    perm_list: List[str] = [
        perm for perm, value in permissions_map.items()
        if value is True
    ]
    return perm_list


def user_list(
    session: Session,
    name: str,
    domain_name: str,
) -> List[str]:
    """List of users with a given role.

    :param Session session: DB session
    :param str name: role name
    :param str domain_name: Corna domain

    :returns: list of users with a given role has
    :rtype: List[str]
    """
    uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role_query: Any = alchemy.role_uuid(session, name, uuid, as_subquery=True)

    core_query: Query = (
        session
        .query(models.role_user_map.columns.user_id)
        .filter_by(role_id=role_query.scalar_subquery())
    )

    users_list: Query = (
        session
        .query(models.UserTable.username)
        .filter(models.UserTable.uuid.in_(core_query))
    )

    # all() returns a nameedtuple when returning a particular column so we do
    # this to turn it into a regular list.
    return [user[0] for user in users_list.all()]


def user_role_list(
    session: Session,
    domain_name: str,
    username: str,
) -> List[str]:
    """Get the list of roles a user has for a given Corna.

    :param Session session: DB session
    :param str domain_name: corna domain name
    :param str username: user to look for

    :returns: a list of roles a user has for a given corna
    :rtype: List[str]
    """
    corna_uuid: Any = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    user_uuid: Any = alchemy.user_uuid(session, username, as_subquery=True)

    role_list: Query = (
        session
        .query(models.role_user_map.columns.role_id)
        .filter_by(user_id=user_uuid)
    )

    user_roles: Query = (
        session
        .query(models.Role.name)
        .filter(models.Role.uuid.in_(role_list))
        .filter(models.Role.corna_uuid == corna_uuid)
    )

    # all() returns a nameedtuple when returning a particular column so we do
    # this to turn it into a regular list.
    return [role[0] for role in user_roles.all()]


def corna_role_list(
    session: Session,
    domain_name: str,
) -> List[str]:
    """List of roles associated with a given Corna.

    :param Session session: DB session
    :param str domain_name: corna domain
    :returns: All roles on a corna
    :rtype: list[str]
    """
    corna_uuid: str = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    role_list: Query = (
        session
        .query(models.Role.name)
        .filter(models.Role.corna_uuid == corna_uuid)
    )

    # all() returns a nameedtuple when returning a particular column so we do
    # this to turn it into a regular list.
    return [role[0] for role in role_list]


def user_perm_list(
    session: Session,
    domain_name: str,
    permission: str,
) -> List[str]:
    """A list of users with a particular permission

    :param Session session: DB session
    :param str domain_name: corna domain
    :param str permission: permission to look for

    :returns: All users with a given permission on a corna
    :rtype: List[str]
    """
    corna_uuid: str = alchemy.corna_uuid(session, domain_name, as_subquery=True)
    perm_value: int = perms.CornaPermissions[permission.upper()]

    role_list: Query = (
        session
        .query(models.Role.uuid)
        .filter(models.Role.corna_uuid == corna_uuid)
        # you can create bitwise operations at SQL level
        .filter(models.Role.permissions.op("&")(perm_value) == perm_value)
    )

    role_to_user_mape: Query = (
        session
        .query(models.role_user_map.columns.user_id)
        .filter(models.role_user_map.columns.role_id.in_(role_list))
    )

    users_list: Query = (
        session
        .query(models.UserTable.username)
        .filter(models.UserTable.uuid.in_(role_to_user_mape))
    )

    # all() returns a nameedtuple when returning a particular column so we do
    # this to turn it into a regular list.
    return [user[0] for user in users_list]
