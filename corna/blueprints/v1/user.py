"""Get information about the 'current user' i.e. user logged in."""

from http import HTTPStatus
from typing import Dict, List, Optional

import flask
from flask_apispec import doc, marshal_with
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields

from corna import enums
from corna.controls import user_control as control
from corna.utils import secure, utils

user = flask.Blueprint("user", __name__)


@user.before_request
def login_required():
    """Check user is logged in."""
    signed_cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )

    if not signed_cookie or not secure.is_valid(signed_cookie):
        utils.respond_json_error(
            "Login required for this action",
            HTTPStatus.UNAUTHORIZED,
        )


@user.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response: a flask response object
    :returns: a flask response object with added security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


class UserDetails(Schema):
    """Schema for user details."""
    username = fields.String(
        metadata={
            "description": "Username of currently logged in user",
        })

    cred = fields.Integer(
        metadata={
            "description": "User CornaCredz",
        })

    role = fields.String(
        metadata={
            "description": "User system role",
        })

    avatar = fields.String(
        metadata={
            "description": "URL for user avatar",
        })


@user.route("/user", methods=["GET"])
@marshal_with(UserDetails(), code=200)
@doc(
    tags=["User"],
    description="Get current user details.",
)
def user_details():
    """Get user details."""
    cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value
    )
    details = control.details(session, cookie)
    return details


class CreatedRoles(Schema):
    """Role name, Corna domain map."""

    domain_name = fields.String()
    name = fields.String()


class CreatedRolesList(Schema):
    """Schema for user created roles."""

    roles = fields.Nested(CreatedRoles, many=True)


@user.route("/user/roles/created", methods=["GET"])
@marshal_with(CreatedRolesList(), code=200)
@doc(
    tags=["User"],
    description="List of roles created by current user.",
)
def get_roles_created():
    """Get all roles created by the current user."""
    cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )
    role_list: List[Dict[str, str]] = control.roles_created(session, cookie)

    return {"roles": role_list}
