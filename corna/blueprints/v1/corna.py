"""Corna management endpoints."""

from http import HTTPStatus
import re
from typing import Any, Dict, Optional, Union

import flask
from flask_apispec import doc, marshal_with, use_kwargs
from marshmallow import Schema, fields

from corna import enums
from corna.controls import corna_control
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import secure, utils
from corna.utils.errors import (
    DomainExistsError, NoneExistingUserError, PreExistingCornaError)
from corna.utils.utils import login_required

corna = flask.Blueprint("corna", __name__)


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

    about_me = fields.String(
        metadata={
            "description": "User bio/about information",
        })

    theme_uuid = fields.UUID(
        metadata={
            "description": "UUID of chosen theme",
        })

    permissions = fields.List(
        fields.String(),
        load_default=["read", "comment", "like", "follow"],
        metadata={
            "description": "Corna wide default permissions. These are the "
                           "permissions used to validate access for any users "
                           "without a more specific role. If blank, the "
                           "default permissions of: read, comment, like, "
                           "follow will be set. For no permissions i.e. "
                           "a private Corna, permissions should be an empty "
                           "list."
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class DomainNameReturnSchema(_BaseSchema):
    """Schema for domain name return."""


class DomainNameAvailableCheck(_BaseSchema):
    """Schema for checking domain name exists."""

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class DomainNameCheckResultSchema(Schema):
    """Result of domain name check schema."""

    domain_name = fields.String(
        metadata={
            "description": "The original domain name being checked",
        })

    available = fields.Boolean(
        metadata={
            "description": "The result of the existence check",
        })


def is_valid(domain: str) -> None:
    """Validate that domain name is formatted correctly.
    
    validates against the following rules:
        - must start and end with: [A-Za-z0-9]
        - can contain a "-" but cannot start or end with one
        - must be less than 20 characters long

    more info:
        - https://stackoverflow.com/a/7933253
        - https://stackoverflow.com/a/7111947

    Note: we don't return anything because if the match fails we abort the
    request.
    
    :param str domain: domain name to validate
    """
    # ending in the pattern is optional i.e. we only care about if the domain
    # ends in [A-Za-z0-9] iff there is more than one character. This is
    # because the other character could potentially be a dash. Thus this
    # regex allows for single character domains.
    # 
    # reason for {0,17}: the domain should be 19 characters at most. This means
    # that the characters in the middle i.e. minus first and last character,
    # need to add up to 17
    pattern: str = r"^[A-Za-z0-9](?:[A-Za-z0-9\-]{0,17}[A-Za-z0-9])?$"
    match = re.search(pattern, domain)

    if not match:
        err_msg: str = (
            "Invalid Corna domain. Domain can only contain letters a-z, "
            "0-9 and dashes. Domain must be less than 20 characters."
        )
        utils.respond_json_error(err_msg, HTTPStatus.UNPROCESSABLE_ENTITY)


@corna.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response: a flask response object
    :returns: a flask response object with added security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


@corna.route("/corna/<domain_name>", methods=["POST"])
@login_required
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
def create_corna(
    domain_name: str,
    **data: Dict[str, Any]
) -> flask.wrappers.Response:
    """Create a new Corna."""
    # ensure domain is valid
    is_valid(domain_name)
    # we need to get the user identity via cookie
    cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value
    )
    data.update({
        "cookie": cookie,
        "domain_name": domain_name.lower(),
    })
    try:
        corna_control.create(session, **data)
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


@corna.route("/corna", methods=["GET"])
@login_required
@marshal_with(DomainNameReturnSchema(), code=200)
@doc(
    tags=["corna"],
    description="Get a users corna domain name",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "user is not logged in",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "User has no corna",
        },
    },
)
def get_domain() -> Dict[str, str]:
    """Get corna domain name for given user."""
    cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value)

    if not cookie:
        utils.respond_json_error("User not logged in", HTTPStatus.BAD_REQUEST)
    try:
        domain: str = corna_control.get_domain(session, cookie)

    except NoneExistingUserError as e:
        utils.respond_json_error(str(e), HTTPStatus.NOT_FOUND)

    return {"domain_name": domain}


@corna.route("/corna/domain/available", methods=["GET"])
@use_kwargs(DomainNameAvailableCheck(), location="query")
@marshal_with(DomainNameCheckResultSchema(), code=200)
@doc(
    tags=["Corna"],
    description="Check if corna domain name is taken",
)
def check_domain_available(domain_name: str) -> flask.wrappers.Response:
    """Check if domain name has been taken."""
    taken: bool = corna_control.domain_unique(session, domain_name)
    outcome: Dict[str: Union[str, bool]] = {
        "domain_name": domain_name,
        "available": taken
    }
    return outcome
