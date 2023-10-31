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


def register_user(session: LocalProxy, user_data: RegisterUser) -> None:
    """Register a new user.

    :param sqlalchemy.Session session: session object
    :param RegisterUser user_data: user data to register
    :raises UserExistsError: if user details are already in use
    """
    user_email: Optional[models.EmailTable] = (
        session
        .query(models.EmailTable)
        .get(user_data["email_address"])
    )
    if user_email is not None:
        raise UserExistsError("Email address already has an account")

    session.add(
        models.EmailTable(
            email_address=user_data["email_address"],
            password=user_data["password"],
        )
    )

    session.add(
        models.UserTable(
            uuid=utils.get_uuid(),
            email_address=user_data["email_address"],
            username=user_data["user_name"],
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
        .get(user_data["email_address"])
    )
    if user_account is None:
        raise NoneExistingUserError("User does not exist")

    if not user_account.is_password(user_data["password"]):
        raise IncorrectPasswordError("Wrong password")

    user: models.UserTable = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.email_address == user_data["email_address"])
        .one()
    )
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
