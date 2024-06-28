"""Controls for 'current user' interfaces."""

import logging
import random
from typing import Dict, List, Optional

# for typing
from sqlalchemy.orm.scoping import scoped_session as Session
from typing_extensions import TypedDict

from corna.db import models
from corna.middleware import alchemy
from corna.utils import utils

logger: logging.Logger = logging.getLogger(__name__)


class UserDetails(TypedDict):
    """User details object."""

    cred: int
    avatar: str
    role: str
    username: str


def build_avatar_url(session: Session, uuid: str) -> str:
    """Build URL for user avatar.

    :param Session session: a db session
    :param str uuid: uuid of avatar
    :returns: complete download URL for an avatar
    :rtype: str
    """
    download_url: str = f"{utils.UNVERSIONED_API_URL}/v1/media/download"
    avatar: models.Media = alchemy.media_from_uuid(session, uuid)
    return f"{download_url}/{avatar.url_extension}"


def details(session: Session, cookie: str) -> UserDetails:
    """Get user details.

    :param Session session: db session
    :param str cookie: user cookie
    :returns: object containing user details
    :rtype: UserDetails
    """
    curr_user: models.UserTable = alchemy.current_user(session, cookie)
    avatar_url: Optional[str] = (
        build_avatar_url(session, curr_user.avatar)
        if curr_user.avatar else None
    )

    user_details: UserDetails = {
        "username": curr_user.username,
        "cred": random.uniform(1, 700),
        "role": "adventurer",
        "avatar": avatar_url,
    }

    return user_details


def roles_created(session: Session, cookie: str):
    """A list of all roles created by a user.

    :param Session session: db session
    :param str cookie: user cookie
    :return: list of roles created by current user
    :rtype: List[Dict[str, str]]
    """
    user_role_list: List[Dict[str, str]] = []
    curr_user = alchemy.current_user(session, cookie)
    # Bad query, this needs to be fixed. This can probably be solved with
    # joins but cannot be bothered to figure out exactly how right now.
    # potential solutions: https://stackoverflow.com/a/50705573
    roles: List[models.Role] = (
        session
        .query(models.Role)
        .filter(models.Role.creator_uuid == curr_user.uuid)
        .all()
    )

    for role in roles:
        corna: models.CornaTable = (
            session
            .query(models.CornaTable)
            .get(role.corna_uuid)
        )

        user_role_list.append(
            {
                "domain_name": corna.domain_name,
                "name": role.name,
            }
        )

    return user_role_list
