"""Manage Auth"""
import logging
from typing import Any, Dict, Optional

from corna.db import models
from corna.utils import secure, utils
from corna.utils.errors import (
    IncorrectPasswordError, NoneExistingUserError, UserExistsError)

logger = logging.getLogger(__name__)


def register_user(session: Any, user_data: Dict[str, str]) -> None:
    """Register a new user.

    :param sqlalchemy.Session session: session object
    :param dict user_data: user data to register
    """
    user_email: Optional[str] = (
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
            date_created=utils.get_utc_now(),
        )
    )
    logger.info("successfully registered a new user.")


def login_user(session: Any, user_data: Dict[str, str]) -> bytes:
    """Login a user.

    :param sqlalchemy.Session session: session object
    :param dict user_data: user data to login
    """
    user_account: Optional[str] = (
        session
        .query(models.EmailTable)
        .get(user_data["email_address"])
    )
    if user_account is None:
        raise NoneExistingUserError("User does not exist")

    if not user_account.is_password(user_data["password"]):
        raise IncorrectPasswordError("Wrong password")

    user: str = (
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


def delete_user_session(session: Any, signed_cookie: str):
    """Delete user session.

    :param sqlalchemy.Session session: session object
    :param str cookie_id: user cookie
    """
    cookie_id = secure.decoded_message(signed_cookie)
    (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .delete(synchronize_session=False)
    )

    logger.info("successfully deleted session")
