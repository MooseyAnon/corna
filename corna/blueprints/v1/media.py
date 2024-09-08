"""Endpoints to manage media files."""

from http import HTTPStatus
from typing import List

import flask
from flask import request
from flask_apispec import doc, marshal_with, use_kwargs
from marshmallow import Schema, fields, validate
from werkzeug.datastructures import FileStorage

from corna import enums
from corna.controls import media_control
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import secure, utils

media = flask.Blueprint("media", __name__)


class FileUploadSend(Schema):
    """SChema for uploading media."""

    type = fields.String(
        validate=validate.OneOf(
            [media_type.value for media_type in enums.MediaTypes]
        ),
        required=True,
        metadata={
            "description": "Media type e.g. audio, image, video etc",
        },
    )

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class FileUploadReturn(Schema):
    """Response on uploading a file."""

    id = fields.String(
        metadata={
            "description": "The ID of the image",
        },
    )

    filename = fields.String(
        metadata={
            "description": "Filename of the file that has been saved,"
        },
    )

    mime_type = fields.String(
        metadata={
            "description": "MIME type of file.",
        },
    )

    size = fields.Integer(
        metadata={
            "description": "File size",
        },
    )

    url_extension = fields.String(
        metadata={
            "description": "URL extension for file",
        },
    )


@media.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response:
    :returns: flask response object with updated headers
    :rtype: flask.Response
    """
    headers = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


@media.route("/media/upload", methods=["POST"])
@utils.login_required
@marshal_with(FileUploadReturn(), code=200)
@use_kwargs(FileUploadSend(), location="form")
@doc(
    tags=["media"],
    description="Upload a media file to the server",
    response={
        HTTPStatus.BAD_REQUEST: {
            "description": "No file to upload sent",
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {
            "description": "Unable to save file",
        },
        HTTPStatus.CREATED: {
            "description": "Successfully saved file",
        },
    }
)
def upload(type: str):  # pylint: disable=redefined-builtin
    """Upload a media file."""

    if not request.files.get("image"):
        utils.respond_json_error("Media file required", HTTPStatus.BAD_REQUEST)

    images: List[FileStorage] = request.files.getlist("image")
    utils.validate_files(images)

    try:
        image_data = media_control.upload(session, images[0], type)

    except OSError:
        utils.respond_json_error(
            "Unable to save file",
            HTTPStatus.INTERNAL_SERVER_ERROR
        )

    session.commit()

    return image_data, HTTPStatus.CREATED


@media.route("/media/download/<url_extension>", methods=["GET"])
@doc(
    tags=["media"],
    description="Download a media file to the server",
    response={
        HTTPStatus.BAD_REQUEST: {
            "description": "No file found",
        },
    }
)
def download(url_extension: str):
    """Download a file from the server."""

    try:
        path: str = media_control.download(session, url_extension)

    except FileNotFoundError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    return flask.send_file(path)


class GenerateAvatarReturn(Schema):
    """Schema for returning a random avatar."""

    url = fields.String(
        metadata={
            "description": "Avatar download URL",
        })

    slug = fields.String(
        metadata={
            "description": "Avatar slug",
        })


@media.route("/media/avatar", methods=["GET"])
@marshal_with(GenerateAvatarReturn(), code=200)
@doc(
    tags=["media"],
    description="Get a random avatar",
)
def gen_avatar():
    """Get URL for a random avatar."""
    return media_control.random_avatar(session)
