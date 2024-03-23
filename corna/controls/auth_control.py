"""Manage Auth"""
import logging
from typing import Optional

from typing_extensions import TypedDict
from werkzeug.local import LocalProxy

from corna.db import models
from corna.utils import get_utc_now, secure, utils
from corna.utils.errors import (
    IncorrectPasswordError, NoneExistingUserError, UserExistsError)

logger = logging.getLogger(__name__)


# **** types ****

class _AuthTypesBase(TypedDict):
    """Shared types."""

    email_address: str
    password: str


class RegisterUser(_AuthTypesBase):
    """Register user types."""

    user_name: str


class LoginUser(_AuthTypesBase):
    """Login user types."""

# **** types end ****


def username_exists(session: LocalProxy, username: str) -> bool:
    """Check if username is taken.

    :param sqlalchemy.Session session: a db session
    :param str username: username to search for
    :returns: True if the username is already taken, else False
    :rtype: bool
    """
    return utils.exists_(session, models.UserTable.username, username)


def email_exists(session: LocalProxy, email: str) -> bool:
    """Check if email is already taken.

    :param sqlalchemy.Session session: a db session
    :param str email: email to search for
    :returns: True if the email is already taken, else False
    :rtype: bool
    """
    return utils.exists_(session, models.EmailTable.email_address, email)


def session_exists(session, user_uuid):
    """Check a user session exists.

    :param sqlalchemy.Session session: a db session
    :param str user_uuid: user uuid to search for
    :returns: True if the user already has a session
    :rtype: bool
    """
    return utils.exists_(session, models.SessionTable.user_uuid, user_uuid)


def register_user(session: LocalProxy, user_data: RegisterUser) -> None:
    """Register a new user.

    :param sqlalchemy.Session session: session object
    :param RegisterUser user_data: user data to register
    :raises UserExistsError: if user details are already in use
    """
    user_email: Optional[models.EmailTable] = (
        session
        .query(models.EmailTable)
        .get(user_data["email"])
    )
    if user_email is not None:
        raise UserExistsError("Email address already has an account")

    session.add(
        models.EmailTable(
            email_address=user_data["email"],
            password=user_data["password"],
        )
    )

    session.add(
        models.UserTable(
            uuid=utils.get_uuid(),
            email_address=user_data["email"],
            username=user_data["username"],
            date_created=get_utc_now(),
        )
    )
    logger.info("successfully registered a new user.")


def login_user(session: LocalProxy, user_data: LoginUser) -> bytes:
    """Login a user.

    :param sqlalchemy.Session session: session object
    :param LoginUser user_data: user data to login
    :raises NoneExistingUserError: if user details do not exist
    :raises IncorrectPasswordError: if password is wrong
    """
    user_account: Optional[models.EmailTable] = (
        session
        .query(models.EmailTable)
        .get(user_data["email"])
    )
    if user_account is None:
        raise NoneExistingUserError("User does not exist")

    if not user_account.is_password(user_data["password"]):
        raise IncorrectPasswordError("Wrong password")

    user: models.UserTable = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.email_address == user_data["email"])
        .one()
    )

    # There are situations where the client has deleted the cookie but it is
    # still present in the database. In order to avoid errors we need to ensure
    # the we remove any uncleared sessions. This is due to our constraint that
    # each user can only have one on-going session at a time.
    if session_exists(session, user.uuid):
        delete_prexisting_session(session, user.uuid)

    cookie: str = secure.generate_unique_token(
        session, models.SessionTable.cookie_id)
    session_id: str = secure.generate_unique_token(
        session, models.SessionTable.session_id)
    session.add(
        models.SessionTable(
            session_id=session_id,
            cookie_id=cookie,
            user_uuid=user.uuid,
        )
    )
    logger.info("successfully logged in user and created session")

    # We want to sign the cookie after its been saved into the DB.
    # The reason for this is because there are weird issues with
    # type conversions in postgres and it seems to want to save
    # the HMAC has hex rather than unicode. This is an issues as
    # it does the lookup comparisons without converting the incoming
    # hash to hex. this leads to guaranteed failures as unicode values
    # will never match the hex ones saved inside the db.
    return secure.sign(cookie)


def delete_user_session(session: LocalProxy, signed_cookie: str) -> None:
    """Delete user session.

    :param sqlalchemy.Session session: session object
    :param str signed_cookie: user cookie
    """
    cookie_id: str = secure.decoded_message(signed_cookie)
    (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .delete(synchronize_session=False)
    )

    logger.info("successfully deleted session")


def delete_prexisting_session(session: LocalProxy, user_uuid: str) -> None:
    """Delete session via user UUID.

    :param LocalProxy session: db session
    :param str user_uuid: The user uuid to delete
    """
    (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.user_uuid == user_uuid)
        .delete(synchronize_session=False)
    )

    logger.info("successfully deleted pre-existing session")
