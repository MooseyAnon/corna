"""Manage Corna's."""

import logging
from typing import List, Optional
import uuid

from werkzeug.local import LocalProxy

from corna.db import models
from corna.middleware import permissions as perms
from corna.utils import get_utc_now, utils
from corna.utils.errors import (
    DomainExistsError, NoneExistingUserError, PreExistingCornaError)
from corna.utils.utils import current_user

logger = logging.getLogger(__name__)


class NoDomainError(ValueError):
    """When user has no domain."""


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


def create(
    session: LocalProxy,
    cookie: str,
    domain_name: str,
    title: str,
    permissions: List[str],
    about_me: Optional[str] = None,
    theme_uuid: Optional[uuid.uuid4] = None,
) -> None:
    """Create a new corna.

    :param sqlalchemy.Session session: db session
    :param str cookie: user cookie
    :param str domain_name: corna domain name
    :param str title: corna title
    :param Optional[str] about_me: corna about section
    :param List[str] permissions: list of corna permissions
    :param Optional[str] theme_uuid: corna theme

    :raises PreExistingCornaError: user has another corna already
    :raises DomainExistsError: domain name not unique
    """
    user: models.UserTable = current_user(
        session, cookie,
        exception=NoneExistingUserError
    )

    if user_has_corna(session, user.uuid):
        # user already has a Corna
        raise PreExistingCornaError("User has pre-existing Corna")

    if not domain_unique(session, domain_name):
        raise DomainExistsError("Domain name in use")

    about_: Optional[str] = about(
        session=session,
        about_content=about_me,
    )

    theme: Optional[str] = str(theme_uuid) if theme_uuid else None

    session.add(
        models.CornaTable(
            uuid=utils.get_uuid(),
            domain_name=domain_name,
            title=title,
            date_created=get_utc_now(),
            user_uuid=user.uuid,
            about=about_,
            theme=theme,
            permissions=perms.create_role(permissions),
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

    new_uuid = utils.get_uuid()
    session.add(
        models.TextContent(
            uuid=new_uuid,
            content=about_content,
            created=get_utc_now(),
            post_uuid=None,
        )
    )
    return new_uuid


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
