"""Manage Corna's."""

import logging
from typing import Optional

from typing_extensions import TypedDict
from werkzeug.local import LocalProxy

from corna.db import models
from corna.utils import get_utc_now, utils
from corna.utils.errors import (
    DomainExistsError, NoneExistingUserError, PreExistingCornaError)
from corna.utils.utils import current_user

logger = logging.getLogger(__name__)


class NoDomainError(ValueError):
    """When user has no domain."""


# **** types ****

class CornaCreate(TypedDict):
    """Types for creating a new corna."""

    domain_name: str
    title: str
    about: str

# **** types end ****


def user_has_corna(session: LocalProxy, user_uuid: str) -> bool:
    """Check is user has a Corna.

    :param sqlalchemy.Session session: a db session
    :param str user_uuid: user_uuid to search for
    :returns: True if the user has a corna, else False
    :rtype: bool
    """
    return utils.exists_(session, models.CornaTable.user_uuid, user_uuid)


def domain_unique(session: LocalProxy, domain: str) -> bool:
    """Validate domain name is unique.

    :param sqlalchemy.Session session: a db session
    :param str domain: domain name to search for
    :returns: True is domain is unique, else false
    :rtype: bool
    """
    return not utils.exists_(session, models.CornaTable.domain_name, domain)


def create(session: LocalProxy, data: CornaCreate) -> None:
    """Create a new corna.

    :param sqlalchemy.Session session: db session
    :param CornaCreate data: data required to create corna

    :raises PreExistingCornaError: user has another corna already
    :raises DomainExistsError: domain name not unique
    """
    user: models.UserTable = current_user(
        session, data["cookie"],
        exception=NoneExistingUserError
    )

    if user_has_corna(session, user.uuid):
        # user already has a Corna
        raise PreExistingCornaError("User has pre-existing Corna")

    if not domain_unique(session, data["domain_name"]):
        raise DomainExistsError("Domain name in use")

    about_: Optional[str] = about(
        session=session,
        about_content=data.get("about"),
    )

    theme: Optional[str] = (
        str(data.get("theme_uuid"))
        if data.get("theme_uuid")
        else None
    )

    session.add(
        models.CornaTable(
            uuid=utils.get_uuid(),
            domain_name=data["domain_name"],
            title=data["title"],
            date_created=get_utc_now(),
            user_uuid=user.uuid,
            about=about_,
            theme=theme,
        )
    )


def about(session: LocalProxy, about_content: str = None) -> str:
    """Save Corna 'about me' content.

    Underneath the hood, 'about me' is saved as a block of
    text content. This allows us to easily edit/update this
    content in the future, while also giving the flexibility of
    a full text object.

    :params LocalProxy session: db session
    :params Optional[str] about_content: the content to save
    :return: uuid of saved data
    :rtype: str
    """
    if not about_content:
        return None

    uuid = utils.get_uuid()
    session.add(
        models.TextContent(
            uuid=uuid,
            content=about_content,
            created=get_utc_now(),
            post_uuid=None,
        )
    )
    return uuid


def get_domain(session: LocalProxy, signed_cookie: str) -> str:
    """Get a users domain for their corna.

    :param sqlalchemy.Session session: a db session
    :param bytes signed_cookie: users cookie

    :returns: user domain name
    :rtype: str
    :raises NoDomainError: no domain associated with user i.e. they
        have not created a corna
    """
    user: models.UserTable = current_user(
        session, signed_cookie,
        exception=NoneExistingUserError
    )

    corna: Optional[models.CornaTable] = (
        session.
        query(models.CornaTable)
        .filter(models.CornaTable.user_uuid == user.uuid)
        .one_or_none()
    )
    if not corna:
        raise NoDomainError("User has no corna")
    return corna.domain_name
