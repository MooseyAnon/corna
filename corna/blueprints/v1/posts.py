"""Endpoints to manage posts on Corna."""
from http import HTTPStatus
from typing import Any, Dict, List

import flask
from flask import request
from flask_apispec import doc, use_kwargs
from flask_sqlalchemy_session import current_session as session
from marshmallow import Schema, fields, validate

from corna.controls import post_control
from corna.controls.post_control import (
    InvalidContentType, NoneExistinCornaError, PostDoesNotExist)
from corna.enums import ContentType, SessionNames
from corna.utils import secure, utils
from corna.utils.errors import CornaOwnerError
from corna.utils.utils import login_required

posts = flask.Blueprint("posts", __name__)


class _BaseSchema(Schema):
    """Any shared fields."""

    type = fields.String(
        validate=validate.OneOf(
            [post_type.value for post_type in ContentType]
        ),
        required=True,
        metadata={
            "description": "the type of content being sent/received"
        },
    )


class TextPost(_BaseSchema):
    """Schema for new text posts."""

    title = fields.String(
        metadata={
            "description": "title of the post",
        },
    )

    content = fields.String(
        required=True,
        metadata={
            "description": "the contents of the post"
        },
    )

    inner_html = fields.String(
        metadata={
            "description": "The html representation of the post"
        }
    )

    uploaded_images = fields.List(
        fields.String,
        metadata={
            "description":
                "A list of pre-uploaded images that are part of the post."
        })

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


class PhotoPost(_BaseSchema):
    """Schema for photo posts."""

    title = fields.String(
        metadata={
            "description": "title of the post",
        },
    )

    caption = fields.String(
        metadata={
            "description": "the caption for the post"
        },
    )

    class Meta:  # pylint: disable=missing-class-docstring
        strict = True


@posts.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response: out going response
    :return: response with security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


# valid locations:
# https://github.com/marshmallow-code/webargs/blob/dev/src/webargs/core.py#L158
@posts.route("/posts/<domain_name>/text-post", methods=["POST"])
@login_required
@use_kwargs(TextPost())
@doc(
    tags=["posts"],
    description="Create a new text post",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Corna or content type issues (check message)",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description":
                "File with wrong extension or photoset (check message)"
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {
            "description": "Unable to save files",
        },
        HTTPStatus.CREATED: {
            "description": "Successfully created post",
        },
    }
)
def text_post(
    domain_name: str,
    **data: Dict[str, Any]
) -> flask.wrappers.Response:
    """Create a text post."""

    data.update(
        dict(
            cookie=flask.request.cookies.get(SessionNames.SESSION.value),
            domain_name=domain_name,
        )
    )

    try:
        post_control.create(session, data=data)

    except (CornaOwnerError, InvalidContentType, NoneExistinCornaError) as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    # only happens on picture saving failure
    except OSError:
        utils.respond_json_error(
            "Unable to save picture", HTTPStatus.INTERNAL_SERVER_ERROR)

    session.commit()
    return "", HTTPStatus.CREATED


@posts.route("/posts/<domain_name>/photo-post", methods=["POST"])
@login_required
@use_kwargs(PhotoPost(), location="form")
@doc(
    tags=["posts"],
    description="Create a new photo post",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Corna or content type issues (check message)",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description":
                "File with wrong extension or photoset (check message)"
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {
            "description": "Unable to save files",
        },
        HTTPStatus.CREATED: {
            "description": "Successfully created post",
        },
    }
)
def photo_post(
    domain_name: str,
    **data: Dict[str, Any]
) -> flask.wrappers.Response:
    """Create photo post."""

    if not request.files.get("images"):
        utils.respond_json_error(
            "Photo post requires images",
            HTTPStatus.BAD_REQUEST
        )

    images: List[Any] = request.files.getlist("images")
    # Marshmallow doesn't want to work with binary blobs/files so
    # we have to do the validation separately
    utils.validate_files(images, maximum=1)
    data.update(dict(images=images))

    data.update(
        dict(
            cookie=flask.request.cookies.get(SessionNames.SESSION.value),
            domain_name=domain_name,
        )
    )

    try:
        post_control.create(session, data=data)

    except (CornaOwnerError, InvalidContentType, NoneExistinCornaError) as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    # only happens on picture saving failure
    except OSError:
        utils.respond_json_error(
            "Unable to save picture", HTTPStatus.INTERNAL_SERVER_ERROR)

    session.commit()
    return "", HTTPStatus.CREATED


@posts.route("/posts/<domain_name>", methods=["GET"])
@doc(
    tags=["posts"],
    description="Get all posts for a corna",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "if no corna is associated with the domain name",
        },
    },
)
def get_all_posts(domain_name: str) -> Dict[Any, Any]:
    """Get all posts for a given cora."""
    try:
        all_posts: Dict[str, Any] = post_control.get(session, domain_name)

    except NoneExistinCornaError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    return flask.jsonify(all_posts)


@posts.route("/posts/<domain_name>/image/<url_extension>", methods=["GET"])
@doc(
    tags=["posts"],
    description="Get an image file",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Post does not exist",
        },
    },
)
def get_image(domain_name: str, url_extension: str) -> flask.wrappers.Response:
    """Get an image file."""
    try:
        path: str = post_control.get_image(session, domain_name, url_extension)

    except PostDoesNotExist as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    return flask.send_file(path)
