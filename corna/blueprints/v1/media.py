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
        media_file = media_control.download(session, url_extension)
        path: str = media_control.to_path(media_file)

    except FileNotFoundError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    if (
        not (media_file.type == enums.MediaTypes.VIDEO)
        or not (
            ranges := media_control.get_range(request.headers, media_file.size)
        )
    ):
        # send full file if not video or does not contain range header
        return flask.send_file(path)

    start, end = ranges
    file_size = media_file.size
    # validate ranges
    if start >= file_size or end >= file_size:
        # Range not satisfiable
        utils.respond_json_error(
            "Invalid ranges", HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)

    length: int = end - start + 1

    response = flask.Response(
        media_control.video_stream(path, start, end),
        status=206,
        mimetype='video/mp4',
        direct_passthrough=True
    )
    response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))

    return response


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


class UploadChunkSendSchema(Schema):
    """Schema for sending data /chunk/upload."""

    chunkIndex = fields.Integer(
        required=True,
        metadata={
            "description": "The number of the chunk (0 indexed) i.e. if there "
                           "are K chunks the index is K - 1.",
        })

    totalChunks = fields.Integer(
        required=True,
        metadata={
            "description": "The total number of chunks for the file upload",
        })

    uploadId = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the upload.",
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class UploadChunkReturnSchema(Schema):
    """Schema for returning data from /chunk/upload."""

    message = fields.String(
        metadata={
            "description": "The response message",
        })

    received = fields.String(
        metadata={
            "description": "number of chunks received",
        })

    total = fields.String(
        metadata={
            "description": "total number of expected chunks",
        })

    uploadId = fields.String(
        metadata={
            "description": "upload ID for the file",
        })


@media.route("/media/chunk/upload", methods=["POST"])
@utils.login_required
# ok so this is an interesting and fucked up discovery, here goes:
# if you don't marshal your response when using `webargs` (flask-apispec
# uses this under the hood), `webargs` will casually decide to wrap you function
# ANYWAYS, wtf???? So it will call `flask.jsonify` on your behalf. This causes
# the endpoint to break if you try to call jsonify/dumps yourself.
#
# This is not obvious at all and fucking stupid. I've just spend about 3 hours
# trying to figure out why a simple `flask.jsonify` call was breaking the
# endpoint. As much a I fuck with FOSS devs and can't complain when I'm using
# other peoples hard work for free, I am allowed to be temporarily pissed off
# at the three hours I will never get back :middle-finger:
#
# Note: later versions have solved this by allowing you to pass:
# `as_kwargs=True`, ensuring webargs is only involved in the deserialization
# step.
@marshal_with(UploadChunkReturnSchema(), code=201)
@use_kwargs(UploadChunkSendSchema(), location="form")
def chunk_uploader(chunkIndex: int, totalChunks: int, uploadId: str):
    """Handle the uploading of media file chunks"""
    chunk = request.files.get("chunk")
    if not chunk:
        utils.respond_json_error("Media file required", HTTPStatus.BAD_REQUEST)

    try:
        ret: dict[str, int | str] = media_control.process_chunk(
            chunk=chunk,
            chunk_index=chunkIndex,
            total_chunks=totalChunks,
            upload_id=uploadId,
        )

    except OSError:
        utils.respond_json_error(
            "Unable to save chunk. Try again.",
            HTTPStatus.INTERNAL_SERVER_ERROR
        )

    return ret, 201


class MergeChunksSendSchema(Schema):
    """Schema for sending data /chunk/merge."""

    filename = fields.String(
        required=True,
        metadata={
            "description": "The name of the file being uploaded",
        })

    uploadId = fields.String(
        required=True,
        metadata={
            "description": "Unique identifier for the upload.",
        })

    contentType = fields.String(
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


@media.route("/media/chunk/merge", methods=["POST"])
@utils.login_required
@marshal_with(FileUploadReturn(), code=201)
@use_kwargs(MergeChunksSendSchema())
def merge_upload_chunks(uploadId: str, filename: str, contentType: str):
    """Merge uploaded chunks."""
    try:
        merged_file = media_control.merge_chunks(
            filename=filename, upload_id=uploadId)
        ret = media_control.upload(session, merged_file, contentType)

    except media_control.MergingError as err:
        # if we're unable to merge, something serious has gone wrong and the
        # caller my need to retry
        code: int = (
            HTTPStatus.BAD_REQUEST
            if str(err) == "Merge in progress" else
            HTTPStatus.INTERNAL_SERVER_ERROR
        )
        utils.respond_json_error(str(err), code)

    except OSError as err:
        # we should cleanup if the file is too big as it will never
        # successfully be saved to the db.
        # If it is some other kind of fs related error, the client can retry
        if "File to large to save" in str(err):
            media_control.clean_chunks(uploadId)

        utils.respond_json_error(str(err), HTTPStatus.INTERNAL_SERVER_ERROR)

    session.commit()
    # defer cleanup as if this fails, we can just do it in the background
    media_control.clean_chunks(uploadId)
    return ret, 201


class UploadStatusReturnSchema(Schema):
    """Return schema for /chunk/status."""

    message = fields.String(
        metadata={
            "description": "status message",
        })

    complete = fields.Boolean(
        metadata={
            "description": "boolean value denoting if backend has received "
                           "all expected chunks for the file",
        })


@media.route("/media/chunk/status/<upload_id>", methods=["GET"])
@marshal_with(UploadStatusReturnSchema(), code=200)
def get_upload_status(upload_id: str):
    """Get status for chunked uploads."""
    try:
        status: int = media_control.chunk_status(upload_id)

    except FileNotFoundError:
        utils.respond_json_error(
            "No upload being processed",
            HTTPStatus.NOT_FOUND,
        )

    except ValueError:
        utils.respond_json_error(
            "Error processing upload metadata",
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    ret_msg: str = (
        f"{status} chunks missing"
        if status > 0 else "upload complete"
    )

    response: dict = {
        "message": ret_msg,
        "complete": status <= 0,
    }

    return response
