"""Auth endpoints.

Passwords will never be seen or stored in plain text. SSL will cover transport,
and then it will be hashed using `werkzeug.security`.
"""
from http import HTTPStatus
import logging
import re
from typing import Any, Dict, Optional, Union

import flask
from flask_apispec import doc, marshal_with, use_kwargs
from marshmallow import Schema, fields, validates

from corna import enums
from corna.controls import auth_control
from corna.middleware.alchemy import NoMediaError
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import secure, utils
from corna.utils.errors import (
    IncorrectPasswordError, NoneExistingUserError, NotLoggedInError,
    UserExistsError)

auth = flask.Blueprint("auth", __name__)

logger = logging.getLogger(__name__)


class _BaseSchema(Schema):
    """Base schema for shared fields."""

    email = fields.Email(
        required=True,
        metadata={
            "description": "user email address"
        })
    password = fields.String(
        required=True,
        metadata={
            "description": "user password"
        })


class UserCreateSchema(_BaseSchema):
    """Schema for a new user."""

    username = fields.String(
        required=True,
        metadata={
            "description": "chosen username of new user"
        })

    avatar = fields.String(
        required=False,
        metadata={
            "description": "slug for chosen user avatar.",
        })

    @validates("username")
    def validate_username(self, username):
        """Validate username is correctly formatted.

        valid username:
            - alphanumeric chars + '-': [A-Za-z0-9_]
            - 1 - 19 characters: 1 >= username.length > 20

        :param str username: the username to validate
        """
        pattern: str = r"^\w{1,19}$"  # same as: ^[A-Za-z0-9_]+$
        # returns None if there is no match:
        # - https://docs.python.org/3/library/re.html#re.Pattern.search
        match = re.search(pattern, username)
        if not match:
            err_msg: str = (
                "Username can only contain letters A-Z (upper or lower), "
                "0-9 and underscores. Must be less than 20 characters."
            )
            utils.respond_json_error(
                err_msg, HTTPStatus.UNPROCESSABLE_ENTITY)

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class LoginSchema(_BaseSchema):
    """Schema for logging in a user."""

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class UsernameCheckSchema(Schema):
    """Schema for checking if username exists."""

    username = fields.String(
        required=True,
        metadata={
            "description": "check if username is in use",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class UsernameCheckResultSchema(Schema):
    """Result of username check schema."""

    username = fields.String(
        metadata={
            "description": "The original username being checked",
        })

    available = fields.Boolean(
        metadata={
            "description": "The result of the existence check",
        })


class EmailCheckSchema(Schema):
    """Schema for checking if an email address is already in use."""

    email = fields.Email(
        required=True,
        metadata={
            "description": "Check if email address is in use"
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class EmailCheckResultSchema(Schema):
    """Result of username check schema."""

    email = fields.Email(
        metadata={
            "description": "The original email being checked",
        })

    available = fields.Boolean(
        metadata={
            "description": "The result of the existence check",
        })


class LoggedInResultSchema(Schema):
    """Result of login status check."""

    is_loggedin = fields.Boolean(
        metadata={
            "description": "Thee result of login status check",
        })


@auth.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response:
    :returns: flask response object with updated headers
    :rtype: flask.Response
    """
    headers: Dict = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


def create_response(
    data: str = "", status: HTTPStatus = HTTPStatus.OK
) -> flask.wrappers.Response:
    """Create a flask response object.

    :param str data: the data to send as part of the response
    :param int status: status code of the response
    :returns: a new flask response object
    :rtype: flask.Response
    """
    response = flask.Response()
    response.data = data
    response.status = status
    return response


def set_cookie(
    response: flask.Response,
    cookie: str,
    **kwargs: Dict[str, Any]
) -> None:
    """Set a cookie on a response object.

    This is essentially a wrapper around flasks own `set_cookie`
    method but we want setting cookies to be outside of the
    endpoint itself to make testing easier later on i.e. we can
    mock this out.

    :param flask.Response response: response object
    :param str cookie: cookie token to set
    :param dict kwargs: optional params to pass into `set_cookie`
    """
    # pylint: disable-next=import-outside-toplevel
    from flask import current_app as app
    cookie_attrs = {
        "httponly": True,
        "key": enums.SessionNames.SESSION.value,
        "samesite": "Lax",
        "secure": True,
        "value": cookie,
    }

    testing = app.config.get("TESTING")
    if not testing:
        cookie_attrs.update({"domain": "mycorna.com"})
    if kwargs:
        cookie_attrs.update(**kwargs)
    response.set_cookie(**cookie_attrs)


@auth.route("/auth/register", methods=["POST"])
@use_kwargs(UserCreateSchema())
@doc(
    tags=["Auth"],
    description="Create a new user.",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Email address already in use or avatar no found",
        },
    }
)
def register_user(**data: Dict) -> flask.wrappers.Response:
    """Register a user."""
    try:
        auth_control.register_user(session, **data)
    except (NoMediaError, UserExistsError) as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    session.commit()
    return create_response(status=HTTPStatus.CREATED)


@auth.route("/auth/login", methods=["POST"])
@use_kwargs(LoginSchema())
@doc(
    tags=["Auth"],
    description="Login a user",
    responses={
        HTTPStatus.NOT_FOUND: {
            "description": "The email address is not found"
        },
        HTTPStatus.BAD_REQUEST: {
            "description": "The entered password is not correct"
        },
    }
)
def login_user(**data: Dict) -> flask.wrappers.Response:
    """Login a user."""
    # check if user is already logged in
    user_cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value)
    if user_cookie is not None:
        logger.info("User already logged in, logging out to start new session")
        auth_control.delete_user_session(session, user_cookie)

    try:
        cookie: str = auth_control.login_user(session, **data)
    except NoneExistingUserError as error:
        return utils.respond_json_error(str(error), HTTPStatus.NOT_FOUND)
    except IncorrectPasswordError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    session.commit()

    response: flask.Response = create_response()
    # ensure cookie is secured
    set_cookie(response=response, cookie=cookie)
    return response


@auth.route("/auth/logout", methods=["POST"])
@doc(
    tags=["Auth"],
    description="Log out a user session"
)
def logout_user() -> flask.wrappers.Response:
    """Logout a user."""
    # check if user is already logged in
    user_cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value)
    if user_cookie is None:
        return HTTPStatus.OK

    auth_control.delete_user_session(session, user_cookie)
    session.commit()

    response = create_response()
    set_cookie(response=response, cookie="", expires=0)
    return response


@auth.route("/auth/username/available", methods=["GET"])
@use_kwargs(UsernameCheckSchema(), location="query")
@marshal_with(UsernameCheckResultSchema(), code=200)
@doc(
    tags=["Auth"],
    description="Check if a username is taken",
)
def check_username_available(username: str) -> flask.wrappers.Response:
    """Check if username is taken.

    This can be used as a quick check during user registration.
    """
    outcome: Dict[str: Union[str, bool]] = {
        "username": username,
        "available": not auth_control.username_exists(session, username)
    }
    return outcome


@auth.route("/auth/email/available", methods=["GET"])
@use_kwargs(EmailCheckSchema(), location="query")
@marshal_with(EmailCheckResultSchema(), code=200)
@doc(
    tags=["Auth"],
    description="Check if email address is taken",
)
def check_email_available(email: str) -> flask.wrappers.Response:
    """Check if email address is already taken."""
    outcome: Dict[str: Union[str, bool]] = {
        "email": email,
        "available": not auth_control.email_exists(session, email)
    }
    return outcome


@auth.route("/auth/login_status", methods=["GET"])
@marshal_with(LoggedInResultSchema(), code=200)
@doc(
    tags=["Auth"],
    description="Check if current user is logged in",
)
def loging_status():
    """Check if current user it logged in."""
    user_cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )
    login_status = {"is_loggedin": False}

    try:
        if user_cookie and utils.current_user(session, user_cookie):
            login_status["is_loggedin"] = True

    except NotLoggedInError:
        # This just confirms that the user is not logged in
        # there is nothing to do.
        pass

    return login_status
