"""Endpoints to manage posts on Corna."""
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

import flask
from flask import request
from flask_apispec import doc, marshal_with, use_kwargs
from flask_sqlalchemy_session import current_session as session
import marshmallow
from marshmallow import(
    fields, Schema, validate, ValidationError, validates_schema)

from corna import enums
from corna.controls import post_control
from corna.controls.post_control import (
    InvalidContentType, NoneExistinCornaError, PostDoesNotExist)
from corna.utils import secure, utils


posts = flask.Blueprint("posts", __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


class _BasePostSchema(Schema):
    """Shared fields for a post."""
    type = fields.String(
        required=True,
        metadata={
            "description": "the type of content being sent/received"
        },
    )


class TextPostSend(_BasePostSchema):
    """Schema for text post."""
    content = fields.String(
        metadata={
            "description": "the contents of the post"
        },
    )
    title = fields.String(
        metadata={
            "description": "title of the post",
        },
    )

    class Meta:
        strict = True


class PicturePostSsend(_BasePostSchema):
    """Schema for picture post."""
    caption = fields.String(
        metadata={
            "description": "the caption associated with picture"
        },
    )

    class Meta:
        strict = True


def is_allowed(filename: str) -> bool:
    """Check if file extension is valid.

    This is lifted straigh out of the flask docs for handling
    file upload.

    :param str filename: the name of the file being uploaded
    :return: True if extension is valid
    :rtype: bool
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate(payload: str, dict_to_pack: Dict[str, str]) -> None:
    """Validate incoming json from create endpoint.

    To make validation work in a sane way we want to split the
    schemas into separate classes, one for each type of post we expect
    to have. Marshmallow doesnt really allow for that kind of polymorphism
    i.e. conditional schema selection, so we need to do it manually.

    :param str payload: incoming payload to post create endpoint
    :param dict dict_to_pack: pass by reference dict to update once payload
        is validated
    """
    # we need to grab the type value first to use as the conditional key
    # however, this means we cant guarantee that the type field has been
    # set before we receive the data so we need to check first
    _type: Optional[str] = payload.get("type")

    if not _type in ("text", "picture"):
        utils.respond_json_error(
            "Incorrect post type", HTTPStatus.UNPROCESSABLE_ENTITY)

    if _type == "text":
        try:
            dict_to_pack.update(
                TextPostSend()
                .load(payload)
            )
        except ValidationError as error:
            utils.respond_json_error(
                str(error), HTTPStatus.UNPROCESSABLE_ENTITY)

    elif _type == "picture":
        try:
            dict_to_pack.update(
                PicturePostSsend()
                .load(payload)
            )
        except ValidationError as error:
            utils.respond_json_error(
                str(error), HTTPStatus.UNPROCESSABLE_ENTITY)


@posts.after_request
def sec_headers(response: flask.Response) -> flask.Response:
    """Add security headers to every response.

    :param flask.Response response: out going response
    :return: response with security headers
    :rtype: flask.Response
    """
    headers: Dict[str, str] = secure.secure_headers()
    response.headers.update(headers)
    return response


# valid locations:
# https://github.com/marshmallow-code/webargs/blob/dev/src/webargs/core.py#L158
@posts.route("/posts/<domain_name>", methods=["POST"])
@doc(
    tags=["posts"],
    description="Create a new post",
    responses={
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "bad form input",
        },
        HTTPStatus.BAD_REQUEST: {
            "description": "File with wrong extension or photoset",
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {
            "description": "Wnable to save file",
        },
        HTTPStatus.CREATED: {
            "description": "Successfully created post",
        },
    }
)
def create_post(domain_name: str) -> Tuple[str, int]:
    """Create post endpoint."""

    data: Dict[str, str] = {}
    validate(flask.request.form, data)
    
    # add user cookie to data
    # -----
    data.update(
        {
            "cookie": flask.request.cookies.get(
                enums.SessionNames.SESSION.value),
            "domain_name": domain_name
        }
    )
    # all pictures should be named picture
    # all extra form data should be sent together
    pictures: Any = request.files.get("pictures")
    if pictures:
        pictures: List[Any] = request.files.getlist("pictures")
        # we only want to deal with single picture posts
        # for now but this pattern will be used for multiple
        # pictures for a single post
        if len(pictures) > 1:
            utils.respond_json_error(
                "Post can only contain a single picture",
                HTTPStatus.UNPROCESSABLE_ENTITY
            )
        for picture in pictures:
            if not is_allowed(picture.filename):
                utils.respond_json_error(
                    "Illegal file extension",
                    HTTPStatus.UNPROCESSABLE_ENTITY
                )

        # add pictures to incoming data
        data.update({"picture": pictures[0]})

    try:
        post_control.create(session, data=data)

    except (InvalidContentType, NoneExistinCornaError) as e:
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
        posts: Dict[str, Any] = post_control.get(session, domain_name)

    except NoneExistinCornaError as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    return flask.jsonify(posts)


@posts.route("/posts/<domain_name>/p/<url_extension>", methods=["GET"])
@doc(
    tags=["posts"],
    description="Get an image file",
    responses={
        HTTPStatus.BAD_REQUEST: {
            "description": "Post does not exist",
        },
    },
)
def get_image(domain_name: str, url_extension: str):
    """Get an image file."""
    try:
        path: str = post_control.get_image(session, domain_name, url_extension)

    except PostDoesNotExist as e:
        utils.respond_json_error(str(e), HTTPStatus.BAD_REQUEST)

    return flask.send_file(path)
