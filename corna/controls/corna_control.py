"""Manage blogs."""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import exists

from corna.db import models
from corna.utils import secure, utils
from corna.utils.errors import (
    DomainExistsError, NoneExistingUserError, PreExistingCornaError)

logger = logging.getLogger(__name__)


class NoDomainError(ValueError):
    """When user has no domain."""


def exists_(session: Any, table_column: Any, check_val: str) -> bool:
    """Check if some value exists in a table

    :param sqlalchemy.Session session: a db session
    :param sqlalchemy.Table.column table_column: name of column to search on
        e.g. UserTable.email_address
    :param str check_val: the value to look for

    :return: True if value exists, else False
    :rtype: bool
    """
    # wrap this in a try and raise error
    return session.query(
        exists().where(table_column == check_val)
    ).scalar()


def domain_unique(session: Any, domain: str) -> bool:
    """Validate domain name is unique.

    :param sqlalchemy.Session session: a db session
    :param str domain: domain name to search for
    :returns: True is domain is unique, else false
    :rtype: bool
    """
    return not exists_(session, models.CornaTable.domain_name, domain)


def create(session: Any, data: Dict[str, Any]) -> None:
    """Create a new corna.

    :param sqlalchemy.Session session: db session
    :param dict data: data required to create corna

    :raises NoneExistingUserError: no user session i.e. not logged in
    :raises PreExistingCornaError: user has another corna already
    :raises DomainExistsError: domain name not unique
    """
    # cookies are signed to we need to decode them for lookups to work
    cookie_id: str = secure.decoded_message(data["cookie"])
    user_session: Optional[object] = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .one_or_none()
    )
    if user_session is None:
        raise NoneExistingUserError("Unable to find user")

    user: object = user_session.user

    if exists_(session, models.CornaTable.user_uuid, user.uuid):
        # user already has a blog
        raise PreExistingCornaError("User has pre-existing blog")

    if not domain_unique(session, data["domain_name"]):
        raise DomainExistsError("Domain name in use")

    session.add(
        models.CornaTable(
            blog_uuid=utils.get_uuid(),
            domain_name=data["domain_name"],
            title=data["title"],
            date_created=utils.get_utc_now(),
            user_uuid=user.uuid,
        )
    )


def get_domain(session: Any, signed_cookie: str) -> str:
    """Get a users domain for their corna.

    :param sqlalchemy.Session session: a db session
    :param bytes signed_cookie: users cookie

    :returns: user domain name
    :rtype: str
    :raises NoneExistingUserError: No user session i.e. not logged in
    :raises NoDomainError: no domain associated with user i.e. they
        have not created a corna
    """
    unsigned_cookie: str = secure.decoded_message(signed_cookie)
    user_session: Optional[object] = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == unsigned_cookie)
        .one_or_none()
    )
    if user_session is None:
        raise NoneExistingUserError("Unable to find user")

    corna: Optional[object] = (
        session.
        query(models.CornaTable)
        .filter(models.CornaTable.user_uuid == user_session.user_uuid)
        .one_or_none()
    )
    if not corna:
        raise NoDomainError("User has no corna")
    return corna.domain_name
