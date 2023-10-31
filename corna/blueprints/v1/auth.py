"""Auth endpoints.

Passwords will never be seen or stored in plain text. SSL will cover transport,
and then it will be hashed using `werkzeug.security`.
"""
from http import HTTPStatus
import logging
from typing import Any, Dict, Optional

import flask
from flask_apispec import doc, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields

from corna import enums
from corna.controls import auth_control
from corna.utils import secure, utils
from corna.utils.errors import (
    IncorrectPasswordError, NoneExistingUserError, UserExistsError)

auth = flask.Blueprint("auth", __name__)

logger = logging.getLogger(__name__)


class _BaseSchema(Schema):
    """Base schema for shared fields."""

    email_address = fields.Email(
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

    user_name = fields.String(
        required=True,
        metadata={
            "description": "chosen username of new user"
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class LoginSchema(_BaseSchema):
    """Schema for logging in a user."""

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


@auth.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response:
    :returns: flask response object with updated headers
    :rtype: flask.Response
    """
    headers: Dict = secure.secure_headers()
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


def set_cookie(response: flask.Response, **kwargs: Dict[str, Any]) -> None:
    """Set a cookie on a response object.

    This is essentially a wrapper around flasks own `set_cookie`
    method but we want setting cookies to be outside of the
    endpoint itself to make testing easier later on i.e. we can
    mock this out.

    :param flask.Response response: response object
    :param dict kwargs: optional params to pass into `set_cookie`
    """
    response.set_cookie(**kwargs)


@auth.route("/auth/register", methods=["POST"])
@use_kwargs(UserCreateSchema())
@doc(
    tags=["Auth"],
    description="Create a new user.",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Email address already in use"
        },
    }
)
def register_user(**data: Dict) -> flask.wrappers.Response:
    """Register a user."""
    try:
        auth_control.register_user(session, data)
    except UserExistsError as error:
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
        cookie: str = auth_control.login_user(session, data)
    except NoneExistingUserError as error:
        return utils.respond_json_error(str(error), HTTPStatus.NOT_FOUND)
    except IncorrectPasswordError as error:
        return utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    session.commit()

    response: flask.Response = create_response()
    # ensure cookie is secured
    set_cookie(
        response,
        value=cookie,
        secure=True,
        httponly=True,
        samesite="Lax",
        key=enums.SessionNames.SESSION.value,
    )
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
    # set empty cookie
    set_cookie(
        response,
        value="",
        expires=0,
        secure=True,
        httponly=True,
        samesite="Lax",
        key=enums.SessionNames.SESSION.value,
    )
    return response
