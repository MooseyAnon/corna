"""Theme management endpoints."""

from http import HTTPStatus
from typing import Dict, List, Optional

import flask
from flask import request
from flask_apispec import doc, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields, validate
# for types
from werkzeug.datastructures import FileStorage

from corna import enums
from corna.controls import theme_control as control
from corna.utils import secure, utils
from corna.utils.errors import NoneExistingUserError

themes = flask.Blueprint("themes", __name__)


class Base(Schema):
    """Shared fields for themes endpoints."""

    creator = fields.String(
        required=True,
        metadata={
            "description": "username of theme creator"
        })
    name = fields.String(
        required=True,
        metadata={
            "description": "name of the theme",
        })
    path = fields.String(
        metadata={
            "description":
                "path to themes main index.html file, relative "
                "to the themes directory."
        })


class ThemeAddSend(Base):
    """Schema for incoming theme data."""

    description = fields.String(
        metadata={
            "description": "Short description of the theme",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class ThemeUpdateStatusSend(Base):
    """Schema for updating status."""

    status = fields.String(
        validate=validate.OneOf(
            [
                state.value for state in
                enums.ThemeReviewState
            ]
        ),
        required=True,
        metadata={
            "description":
                "The current status of the PR associated with the "
                "theme. I.e. this is essentially a state change."
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


@themes.before_request
def login_required() -> None:
    """Check if user is logged in."""
    signed_cookie: Optional[str] = flask.request.cookies.get(
        enums.SessionNames.SESSION.value)

    if not signed_cookie or not secure.is_valid(signed_cookie):
        utils.respond_json_error(
            "Login required for this action",
            HTTPStatus.UNAUTHORIZED,
        )


@themes.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response: a flask response object
    :returns: a flask response object with added security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers()
    response.headers.update(headers)
    return response


@themes.route("/themes", methods=["POST"])
@use_kwargs(ThemeAddSend(), location="form")
@doc(
    tags=["themes"],
    description="Add a new theme",
    responses={
        HTTPStatus.UNAUTHORIZED: {
            "Description": "Current user not logged in",
        },
        HTTPStatus.BAD_REQUEST: {
            "description": "Theme does not exist or is wrong file type",
        },
    }
)
def add_theme(**data: Dict[str, str]) -> flask.wrappers.Response:
    """Add new theme."""

    if request.files.get("thumbnail"):
        thumbnails = request.files.getlist("thumbnail")
        # Marshmallow doesn't want to work with binary blobs/files so
        # we have to do the validation separately
        utils.validate_files(thumbnails, maximum=1)
        data.update(dict(thumbnail=thumbnails[0]))

    cookie: str = flask.request.cookies[enums.SessionNames.SESSION.value]
    try:
        control.add(session, cookie, data)

    except NoneExistingUserError as error:
        utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    except ValueError as error:
        utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    session.commit()
    return "", HTTPStatus.CREATED


@themes.route("/themes/status", methods=["PUT"])
@use_kwargs(ThemeUpdateStatusSend())
@doc(
    tags=["themes"],
    description="Update theme PR status",
    responses={
        HTTPStatus.UNAUTHORIZED: {
            "Description": "Current user not logged in",
        },
        HTTPStatus.BAD_REQUEST: {
            "description":
                "Issues with theme path, read error message for "
                "more details.",
        },
    }
)
def update_status(**data) -> flask.wrappers.Response:
    """Update theme status."""

    cookie: str = flask.request.cookies[enums.SessionNames.SESSION.value]

    try:
        control.update(session, cookie, data)

    except NoneExistingUserError as error:
        utils.respond_json_error(str(error), HTTPStatus.UNAUTHORIZED)

    except ValueError as error:
        utils.respond_json_error(str(error), HTTPStatus.BAD_REQUEST)

    session.commit()
    return "", HTTPStatus.OK
