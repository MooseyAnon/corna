"""Theme management endpoints."""

from http import HTTPStatus
from typing import Dict, List, Optional

import flask
from flask import request
from flask_apispec import doc, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields
# for types
from werkzeug.datastructures import FileStorage

from corna import enums
from corna.controls import theme_control as control
from corna.utils import secure, utils
from corna.utils.errors import NoneExistingUserError

themes = flask.Blueprint("themes", __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


class ThemeAddSend(Schema):
    """Schema for incoming theme data."""

    creator = fields.String(
        required=True,
        metadata={
            "description": "username of theme creator"
        })
    name = fields.String(
        metadata={
            "description": "name of the theme",
        })
    description = fields.String(
        metadata={
            "description": "Short description of the theme",
        })
    path = fields.String(
        metadata={
            "description": \
                "path to themes main index.html file, relative "
                "to the themes directory."
        })


def is_allowed(filename: str) -> bool:
    """Check if file extension is valid.

    This is lifted straight out of the flask docs for handling
    file upload.

    :param str filename: the name of the file being uploaded
    :return: True if extension is valid
    :rtype: bool
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_thumbnails(images: List[FileStorage]) -> bool:
    """Validate incoming images.

    :param List[FileStorage] images: images to validate
    """
    # there should be only 1 thumbnail for a theme
    if len(images) > 1:
        utils.respond_json_error(
            "Theme can only have a single thumbnail",
            HTTPStatus.UNPROCESSABLE_ENTITY
        )
    for image in images:
        if not is_allowed(image.filename):
            utils.respond_json_error(
                "Illegal file extension",
                HTTPStatus.UNPROCESSABLE_ENTITY
            )


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
        validate_thumbnails(thumbnails)
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
