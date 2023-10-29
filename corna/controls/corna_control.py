"""Manage Corna's."""

import logging
from typing import Any, Optional

from sqlalchemy import exists

from corna.db import models
from corna.utils import get_utc_now
from corna.utils import utils
from corna.utils.utils import current_user
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

    :raises PreExistingCornaError: user has another corna already
    :raises DomainExistsError: domain name not unique
    """
    user: object = current_user(
        session, data["cookie"],
        exception=NoneExistingUserError
    )

    if exists_(session, models.CornaTable.user_uuid, user.uuid):
        # user already has a Corna
        raise PreExistingCornaError("User has pre-existing Corna")

    if not domain_unique(session, data["domain_name"]):
        raise DomainExistsError("Domain name in use")

    session.add(
        models.CornaTable(
            uuid=utils.get_uuid(),
            domain_name=data["domain_name"],
            title=data["title"],
            date_created=get_utc_now(),
            user_uuid=user.uuid,
        )
    )


def get_domain(session: Any, signed_cookie: str) -> str:
    """Get a users domain for their corna.

    :param sqlalchemy.Session session: a db session
    :param bytes signed_cookie: users cookie

    :returns: user domain name
    :rtype: str
    :raises NoDomainError: no domain associated with user i.e. they
        have not created a corna
    """
    user: object = current_user(
        session, signed_cookie,
        exception=NoneExistingUserError
    )

    corna: Optional[object] = (
        session.
        query(models.CornaTable)
        .filter(models.CornaTable.user_uuid == user.user_uuid)
        .one_or_none()
    )
    if not corna:
        raise NoDomainError("User has no corna")
    return corna.domain_name
