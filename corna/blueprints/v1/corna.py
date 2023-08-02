"""Corna management endpoints."""

from http import HTTPStatus
import logging
from typing import Any, Dict, Optional

import flask
from flask_apispec import doc, marshal_with, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields

from corna import enums
from corna.controls import corna_control
from corna.utils.errors import (
    DomainExistsError, NoneExistingUserError, PreExistingCornaError)
from corna.utils import secure, utils

corna = flask.Blueprint("corna", __name__)

logger = logging.getLogger(__name__)


class _BaseSchema(Schema):
    """Base schema for shared fields."""
    domain_name = fields.String(
        required=True,
        metadata={
            "description": "chosen domain of corna",
        })


class CornaCreateSchema(Schema):
    """Schema for creating corna."""
    title = fields.String(
        required=True,
        metadata={
            "description": "title of the corna"
        })

    class Meta:
        strict = True


class CornaUserDetailsSend(Schema):
    """Return basic user details."""

    domain_name = fields.String(
        metadata={
            "description": "chosen domain of corna",
        })
    username = fields.String(
        metadata={
            "description": "username"
        })


@corna.after_request
def sec_headers(response: flask.Response) -> flask.Response:
    """Add security headers to every response.

    :param flask.Response response: a flask response object
    :returns: a flask response object with added security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers()
    response.headers.update(headers)
    return response


@corna.route("/corna/<domain_name>", methods=["POST"])
@use_kwargs(CornaCreateSchema())
@doc(
    tags=["corna"],
    description="Create a new corna",
    responses={
        HTTPStatus.NOT_FOUND: {
            "description": "User not found.",
        },
        HTTPStatus.BAD_REQUEST: {
            "description": "User already has corna or domain in use",
        },
    }
)
def create_corna(domain_name: str, **data: Dict[str, Any]) -> flask.Response:
    """Create a new Corna."""
    # we need to get the user identity via cookie
    cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value
    )
    data.update({
        "cookie": cookie,
        "domain_name": domain_name,
    })
    try:
        corna_control.create(session, data)
    except NoneExistingUserError as e:
        utils.respond_json_error(str(e), HTTPStatus.NOT_FOUND)
    except PreExistingCornaError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)
    except DomainExistsError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)
    # commit session
    session.commit()

    response = flask.Response()
    response.status = HTTPStatus.CREATED
    return response


@corna.route("/corna/user-details", methods=["GET"])
@marshal_with(CornaUserDetailsSend(), 200)
@doc(
    tags=["corna"],
    description="Get a basic user details",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "user is not logged in",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "User has no corna",
        },
    },
)
def get_user_details() -> Dict[str, str]:
    """Get basic user details."""
    cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value)

    # users dont have to create corna's on registering
    domain: Optional[str] = None

    if not cookie:
        utils.respond_json_error("User not logged in", HTTPStatus.BAD_REQUEST)
    try:
        username: str = corna_control.get_username(session, cookie)
        domain = corna_control.get_domain(session, username)

    except corna_control.NoDomainError as error:
        logger.warning(error)

    except NoneExistingUserError as e:
        utils.respond_json_error(str(e), HTTPStatus.NOT_FOUND)

    data: Dict[str, str] = {
        "domain_name": domain,
        "username": username
    }
    return data
