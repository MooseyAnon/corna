"""Validation rules for various parts of our systems."""

import logging
from typing import Optional

from sqlalchemy.orm.query import Query
from sqlalchemy.orm.scoping import scoped_session as Session

from corna.db import models
from corna.middleware import alchemy, permissions as perms
from corna.utils import errors

logger = logging.getLogger(__name__)


def _user_has_perm(
    session: Session,
    perm: int,
    domain_name: str,
    username: Optional[str] = None,
) -> bool:
    """Check if user has a role with a given permission.

    Here we essentially want to check all the roles a user has on a given
    Corna and check if any of those roles have the given permission.

    :param Session session: a DB session
    :param int perm: the permission to check for
    :param str domain_name: domain of the Corna to check
    :param Optional[str] username: username

    :returns: true, if user has role else false
    :rtype: bool
    """
    # fail fast
    if not username:
        return False

    # check perms
    user_uuid: Query = alchemy.user_uuid(session, username, as_subquery=True)
    corna_uuid: Query = alchemy.corna_uuid(
        session, domain_name, as_subquery=True)

    role_id_list: Query = (
        session
        .query(models.role_user_map.columns.role_id)
        .filter(models.role_user_map.columns.user_id == user_uuid)
    )

    role_list: Query = (
        session
        .query(models.Role)
        .filter(models.Role.uuid.in_(role_id_list))
        .filter(models.Role.permissions.op("&")(perm) != 0)
        .filter(models.Role.corna_uuid == corna_uuid)
    )

    result: int = role_list.count()
    return result >= 1  # user has at least one role matching {perm}


def is_owner(
    session: Session,
    domain_name: str,
    username: Optional[str] = None
) -> bool:
    """Check if user owns a Corna.

    :param Session session: db session
    :param str domain_name: the domain name of the corna
    :param str username: username
    :returns: true if user owns the Corna
    :rtype: bool
    """
    if not username:
        return False

    user_uuid: Query = alchemy.user_uuid(session, username, as_subquery=True)

    owner_check: Query = (
        session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == domain_name)
        .filter(models.CornaTable.user_uuid == user_uuid)
    )

    return alchemy.one_or_none(owner_check) is not None


def can_read(
    session: Session,
    domain_name: str,
    username: Optional[str] = None
) -> bool:
    """Check if user has read access on a Corna.

    :param Session session: db session
    :param str domain_name: the domain name of the corna
    :param Optional[str] username: username
    :returns: true if user owns can read
    :rtype: bool
    """
    read_perm: int = perms.CornaPermissions.READ
    try:
        corna_permissions: int = alchemy.corna(  # type: ignore[assignment]
            session, domain_name, "permissions")
    except errors.CornaNotFoundError:
        return False

    res: bool = (
        is_owner(session, domain_name, username)
        or perms.has_perm(corna_permissions, "read")
        or _user_has_perm(session, read_perm, domain_name, username)
    )

    return res


def can_write(session: Session, domain_name: str, username: str) -> bool:
    """Check if user has write access on a Corna.

    :param Session session: db session
    :param str domain_name: the domain name of the corna
    :param Optional[str] username: username
    :returns: true if user owns can read
    :rtype: bool
    """
    write_perm: int = perms.CornaPermissions.WRITE
    try:
        corna_permissions: int = alchemy.corna(  # type: ignore[assignment]
            session, domain_name, "permissions")
    except errors.CornaNotFoundError:
        return False

    res: bool = (
        is_owner(session, domain_name, username)
        or perms.has_perm(corna_permissions, "write")
        or _user_has_perm(session, write_perm, domain_name, username)
    )

    return res


def can_change_permissions(
    session: Session,
    domain_name: str,
    username: str,
) -> bool:
    """Check if a user has authorization to change/update roles."""
    change_perm: int = perms.CornaPermissions.CHANGE_PERMISSIONS
    try:
        corna_permissions: int = alchemy.corna(  # type: ignore[assignment]
            session, domain_name, "permissions")
    except errors.CornaNotFoundError:
        return False

    res: bool = (
        is_owner(session, domain_name, username)
        or perms.has_perm(corna_permissions, "change_permissions")
        or _user_has_perm(session, change_perm, domain_name, username)
    )

    return res
