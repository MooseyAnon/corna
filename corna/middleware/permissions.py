"""Permissions management."""

import enum
import logging
from typing import Dict, List

logger: logging.Logger = logging.getLogger(__name__)


class CornaPermissions(enum.IntEnum):
    """Permission options for a Corna."""

    READ = 0x1
    WRITE = 0x2
    EDIT = 0x4
    DELETE = 0x8
    CHANGE_THEME = 0x10
    CHANGE_PERMISSIONS = 0x20
    COMMENT = 0x40
    LIKE = 0x80
    FOLLOW = 0x100

    @classmethod
    def has_key(cls, key: str) -> bool:
        """Check if CornaPermissions has a certain key.

        :param enum.EnumType cls: instance of the class
        :param str key: the key to search for
        :returns: True if key exists, else False
        :rtype: bool
        """
        return key in cls.__members__


# number of bits in our threshold
# more info: https://stackoverflow.com/a/19617280
THRESHOLD: int = (1 << len(CornaPermissions)) - 1


def create_role(permissions: List[str]) -> int:
    """Create a 'role' based on a given set of permissions.

    :param List[str] permissions: list of permissions that make up the role.
    :return: the final role value
    :rtype: int
    """
    res: int = 0
    for permission in permissions:
        perm: str = permission.upper()
        if not CornaPermissions.has_key(perm):
            logger.warning("%s not found in CornaPermissions")
            continue

        res |= CornaPermissions[perm]

    return res


def perms(role: int) -> Dict[str, bool]:
    """Get all permissions a role has.

    :param int role: the role to check
    :returns: dict containing all permissions, if role has a permission it
        is marked True, else False
    :rtype: Dict[str, bool]
    """
    out: Dict[str, bool] = {}
    for key in CornaPermissions:
        if (key & role) != 0:
            out[key.name.lower()] = True
        else:
            out[key.name.lower()] = False
    return out


def has_perm(role: int, permission: str) -> bool:
    """Check if a given role has a particular permission.

    :param int role: the role being checked
    :param str permission: the permission to check for
    :returns: true if role has permission else false
    :rtype: bool
    """
    perm: str = permission.upper()
    res: bool = False
    if CornaPermissions.has_key(perm):
        # This only works because we are doubling each of the permissions i.e.
        # setting the left most bit of each permission (1, 2, 4, 8 etc).
        # As a result, if we '&' a permission against a role, it will typically
        # result in the original value of the permission being return i.e.
        # 4 & 4 == 4 or 4 & 2 == 2 because of the fact that each permission
        # is double the value of the previous perm.
        res = (CornaPermissions[perm] & role) != 0
    return res


def remove_perm(role: int, permission: str) -> int:
    """Remove a permission from a role.

    :param int role: role to change
    :param str permission: permission to remove
    :returns: a new role without the given permission - if the role
        has the permission, else same role will be returned
    rtype: int
    """
    perm: str = permission.upper()
    if not CornaPermissions.has_key(perm):
        logger.warning("there is not permission named %s", perm)
        # just return role as the permission has not been found in our
        # permissions enum
        return role

    return role & ~CornaPermissions[perm]


def add_perm(role: int, permission: str) -> int:
    """Add a permission to a role.
    :param int role: role to change
    :param str permission: permission to add
    """
    perm: str = permission.upper()
    if not CornaPermissions.has_key(perm):
        logger.warning("there is not permission named %s", perm)
        # just return role as the permission has not been found in our
        # permissions enum
        return role

    return role | CornaPermissions[perm]
