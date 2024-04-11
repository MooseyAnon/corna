"""Wrapper around SQLAchemy functions to 'safely' run queries.

The core reason for this file is to centralise interaction with SQLAlchemy
queries so we can catch errors and handle them properly.

Notes on typing:
SQLAchlemy doesn't do typing very well without third party packages. This is
doubly true for generic functions such as the ones in this file which return
arbitrary rows in the db. This explains the over use of Any in this file.
"""

import logging
from typing import Any, Callable, Optional, TypeVar, Union

from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.scoping import scoped_session as Session

from corna.db import models
from corna.utils import secure
from corna.utils.errors import CornaNotFoundError, NotLoggedInError

logger: logging.Logger = logging.getLogger(__name__)

T = TypeVar("T")


class NoMatchingColumnFundError(ValueError):
    """Raised if table does not have a column."""


def one_or_none(
    incoming_query: Query,
    raise_: bool = False
) -> Optional[Any]:
    """Wrapper around query.one_or_none().

    :param Query incoming_query: the query to run
    :param bool raise_: boolean to raise any errors that occur.
    :returns: the result of the query, ensuring it is either a single result or
        None
    :rtype: Optional[DeclarativeMeta]
    :raises MultipleResultsFound:
    """
    # This is actually of type DeclarativeMeta but that part if SQLAlchemy does
    # not have the appropriate type stubs and cannot be followed at import
    # time.
    result: Optional[Any] = None
    try:
        result = incoming_query.one_or_none()

    except MultipleResultsFound as e:
        logger.error(e)
        if raise_:
            raise e

    return result


def scalar(
    incoming_query: Any,
    raise_: bool = False
) -> Optional[Any]:
    """Wrapper around query.scalar().

    :param Query incoming_query: the query to run
    :param bool raise_: boolean to raise any errors that occur.
    :returns: the first item in the result of the query
    :rtype: Optional[DeclarativeMeta]
    :raises MultipleResultsFound:
    """

    result: Optional[Any] = None
    try:
        result = incoming_query.scalar()

    except MultipleResultsFound as e:
        logger.error(e)
        if raise_:
            raise e

    return result


def _column_to_return(
    table: T,
    column: Optional[str] = None,
) -> Union[Any, T]:
    """Finds Columns to be returned on table.

    If not column is present we return the 'table' value which selects
    all rows from the table.

    :param T table: orm representation of a table in the DB
    :param Optional[str] column: column name, if we only want to return a
        single column
    :returns: a column or a reference to the entire table
    :rtype: Union[Any, T]
    :raises NoMatchingColumnFundError: if table does not have a column with
        the name passed in the column argument.
    """
    if column and not hasattr(table, column):
        logger.error(
            "%s table has no column %s",
            table.__tablename__, column  # type: ignore[attr-defined]
        )
        raise NoMatchingColumnFundError("Column not found")

    return getattr(table, column) if column else table


def _query(
    session: Session,
    table: T,
    other: str,
    return_object: T,
    filter_column: str = "uuid",
) -> Query:
    """Form a simple query.

    Note this is a private method which should only be used by the query
    wrapper function in this module and not directly accessed.

    :param Session session: db session
    :param T table: orm representation of a table in the db
    :param str other: comparator value
    :param T return_object: value being 'selected' i.e. a all columns or a
        single column
    :param str filter_column: value used to filter in query

    :return: a formed query
    :rtype: Query
    """
    prepped_query: Query = (
        session
        .query(return_object)
        .filter(getattr(table, filter_column) == other)
    )
    return prepped_query


def query(
    session: Session,
    table: T,
    other: str,
    filter_column: str = "uuid",
    return_column: Optional[str] = None,
    raise_: bool = False
) -> Query:
    """Form a simple query.

    :param Session session: db session
    :param T table: orm representation of a table in the db
    :param str other: comparator value
    :param str filter_column: value used to filter in query
    :param Optional[str] return_column: column to select, if empty all columns
        in table will be returned
    :param bool raise_: raise any errors caught

    :return: a formed query
    :rtype: Query
    :raises NoMatchingColumnFundError: if table has no matching return_column
    """

    try:
        ret_object: T = (
            _column_to_return(table, return_column)
            if return_column else table
        )

    except NoMatchingColumnFundError as e:
        if raise_:
            raise e
        return None

    return _query(
        session,
        table,
        other,
        ret_object,
        filter_column,
    )


def uuid(
    session: Session,
    table: T,
    other: str,
    filter_column: str = "uuid"
) -> Optional[str]:
    """Return uuid of any matching column on given query.

    :param Session session: db session
    :param T table: orm representation of a table in the db
    :param str other: comparator value
    :param str filter_column: value used to filter in query

    :return: uuid of matching value or None
    :rtype: Optional[Any]
    """
    query_: Query = query(
        session,
        table,
        other,
        filter_column=filter_column,
        return_column="uuid"
    )
    return scalar(query_) if query_ else None


def uuid_subquery(
    session: Session,
    table: T,
    other: str,
    filter_column: str = "uuid",
) -> Optional[Any]:
    """Return uuid subquery.

    :param Session session: db session
    :param T table: orm representation of a table in the db
    :param str other: comparator value
    :param str filter_column: value used to filter in query

    :return: subquery for finding some uuid in some table
    :rtype: Optional[Any]
    """
    query_: Query = query(
        session,
        table,
        other,
        filter_column=filter_column,
        return_column="uuid"
    )
    return query_.scalar_subquery() if query_ else None


def delete(
    session: Session,
    table: T,
    other: str,
    filter_column: str,
) -> None:
    """Delete a db entry.

    :param Session session: db session
    :param T table: orm representation of a table in the db
    :param str other: comparator value
    :param str filter_column: value used to filter in query
    """
    query_: Query = query(
        session,
        table,
        other,
        filter_column=filter_column,
    )
    query_.delete(synchronize_session=False)


def current_user(
    session: Session,
    cookie: str,
    exception: type = NotLoggedInError,
) -> models.UserTable:
    """Return the current user.

    This function returns an instance of the current user depending
    on the given session cookie.

    :param Session session: a db session
    :param str cookie: a signed cookie
    :param Optional[type] exception: Custom exception to raise on failure

    :return: a user object
    :rtype: models.UserTable
    :raises exception: if user is not logged in
    """
    cookie_id: str = secure.decoded_message(cookie)

    user_uuid_: Query = query(
        session,
        models.SessionTable,
        cookie_id,
        filter_column="cookie_id",
        return_column="user_uuid",
    )

    user_query: Query = query(
        session,
        models.UserTable,
        user_uuid_.scalar_subquery(),
        filter_column="uuid",
    )

    try:
        user_: Optional[models.UserTable] = one_or_none(user_query, raise_=True)

    except MultipleResultsFound as e:
        logger.error("multiple users matching cookie with id: %s", cookie_id)
        raise exception("Cannot find user") from e

    if not user_:
        raise exception("User not logged in")
    # we have found our user
    return user_


def corna(
    session: Session,
    domain_name: str,
    return_column: Optional[str] = None,
) -> Optional[Union[Any, models.CornaTable]]:
    """Get Corna matching the given domain name.

    :param Session session: db session
    :param str domain_name: the Corna domain_name
    :param Optional[str] return_column: column to select, if empty all columns
        in table will be returned
    :returns: Corna information associated with the subdomain
    :rtype: model.Corna
    :raises CornaNotFoundError: if there is no corna for subdomain
    """
    corna_query: Query = query(
        session,
        models.CornaTable,
        domain_name,
        filter_column="domain_name",
        return_column=return_column
    )

    result: Optional[Union[Any, models.CornaTable]] = scalar(corna_query)
    # result can be 0 because of a value inside the DB, which is a falsey
    # value. We need to be explicit with our check here
    if result is None:
        logger.warning("No corna named %s found", domain_name)
        raise CornaNotFoundError(
            f"No Corna with the domain {domain_name} found.")

    return result


def corna_uuid(
    session: Session,
    other: str,
    filter_column: str = "domain_name",
    as_subquery: Optional[bool] = False,
) -> Optional[Union[Any, str]]:
    """Get Corna uuid.

    :param Session session: db session
    :param str other: comparator value e.g. domain name or other attr
    :param str filter_column: value used to filter in query
    :param bool as_subquery: return the query without evaluating it, usually
        to be uses as a subquery

    :returns: either a query or a uuid
    :rtype: Optional[Union[Any, str]]
    """
    func: Callable[[Session, T, str, str], Optional[str]]
    if as_subquery:
        func = uuid_subquery
    else:
        func = uuid

    result: Optional[Union[Any, str]] = func(
        session=session,
        table=models.CornaTable,
        other=other,
        filter_column=filter_column,
    )

    return result


def user(
    session: Session,
    username: str,
    filter_column: str = "username",
) -> Optional[models.UserTable]:
    """Get a user object from the DB.

    :param Session session: db session
    :param str username: username
    :param str filter_column: value used to filter in query

    :returns: user object, if found
    :rtype: Optional[models.UserTable]
    :raises MultipleResultsFound: if query returns more than one result
    """
    user_query: Query = query(
        session=session,
        table=models.UserTable,
        other=username,
        filter_column=filter_column,
    )

    try:
        user_: Optional[models.UserTable] = one_or_none(user_query, raise_=True)

    except MultipleResultsFound as e:
        logger.error("multiple users matching username: %s", username)
        raise e

    return user_


def user_uuid(
    session: Session,
    other: str,
    filter_column: str = "username",
    as_subquery: bool = False,
) -> Optional[Union[Any, str]]:
    """Get user UUID.

    :param Session session: db session
    :param str other: comparator value e.g. username or other attr
    :param str filter_column: value used to filter in query
    :param bool as_subquery: return the query without evaluating it, usually
        to be uses as a subquery

    :returns: either a query or a uuid
    :rtype: Optional[Union[Any, str]]
    """
    func: Callable[[Session, T, str, str], Optional[str]]
    if as_subquery:
        func = uuid_subquery
    else:
        func = uuid

    result: Optional[Union[Any, str]] = func(
        session=session,
        table=models.UserTable,
        other=other,
        filter_column=filter_column,
    )

    return result


def _get_role_query(
    session: Session,
    name: str,
    uuid_: Union[Any, str],
    filter_column: models.Role,
    return_column: models.Role,
) -> Query:
    """Form query for getting a role.

    :param Session session: a DB session
    :param str name: role name
    :param Union[Any, str] uuid_: a corna uuid or uuid subquery
    :param models.Role filter_column: column to filter results
    :param models.Role return_column: column to return, returns full object
        if no column is specified

    :return: a query to be evaluated
    :rtype: Query
    """
    role_query: Query = (
        session
        .query(return_column)
        .filter(filter_column == uuid_)
        .filter(models.Role.name == name.lower())
    )

    return role_query


def role(
    session: Session,
    name: str,
    uuid_: Union[Any, str],
    filter_column: str = "corna_uuid",
    return_column: Optional[str] = None,
    as_subquery: bool = False,
) -> Optional[Union[Query, models.Role]]:
    """Get a role object from the DB.

    :param Session session: a DB session
    :param str name: role name
    :param Any uuid_: a corna uuid or uuid subquery
    :param models.Role filter_column: column to filter results
    :param models.Role return_column: column to return, returns full object
        if no column is specified
    :param bool as_subquery: return the query without evaluating

    :return: a query to be evaluated or a role object
    :rtype: Optional[Union[Query, models.Role]]
    :raises NoMatchingColumnFundError: if return or filter columns are not
        present on the table.
    :raises MultipleResultsFound: if query returns more than one result
    """
    try:
        comparator: models.Role = _column_to_return(
            models.Role, filter_column)
        ret_col: models.Role = _column_to_return(
            models.Role, return_column)

    except NoMatchingColumnFundError as e:
        raise e

    role_query: Query = _get_role_query(
        session=session,
        name=name,
        uuid_=uuid_,
        filter_column=comparator,
        return_column=ret_col,
    )

    if as_subquery:
        return role_query

    try:
        result: Optional[models.Role] = one_or_none(role_query)

    except MultipleResultsFound as e:
        logger.error("multiple users matching role named: %s", name)
        raise e

    return result


def role_uuid(
    session: Session,
    name: str,
    corna_uuid_: Union[Any, str],
    as_subquery: bool = False,
) -> Optional[Union[Query, models.Role]]:
    """Get role UUID.

    :param Session session: a DB session
    :param str name: role name
    :param str corna_uuid_: a corna uuid or uuid subquery
    :param bool as_subquery: return the query without evaluating

    :returns: a query to be evaluated or a role object
    :rtype: Optional[Union[Query, models.Role]]
    """
    result: Optional[Union[Query, models.Role]] = role(
        session,
        name,
        corna_uuid_,
        return_column="uuid",
        as_subquery=as_subquery,
    )
    return result
