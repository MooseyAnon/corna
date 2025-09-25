"""Utilities for `corna`."""

import collections.abc
from copy import deepcopy
from functools import lru_cache, wraps
from http import HTTPStatus
import io
import json
import logging
import mimetypes
import pathlib
import random
import shutil
import string
from typing import Any, Callable, List, Optional, Tuple
import uuid

import apispec
import flask
from marshmallow import fields, missing as marshmallow_missing
import nh3
import requests
from sqlalchemy import exists
import validators
from werkzeug.datastructures import FileStorage
from werkzeug.local import LocalProxy

from corna import enums
from corna.controls.marshmallow_control import BaseSchema
from corna.db import models
from corna.utils import secure
from corna.utils.errors import NotLoggedInError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: Tuple[str, ...] = tuple(
    extension.value
    for extension in enums.AllowedExtensions
)

# these are the tags the can be sent by the text editor
ALLOWED_HTML_TAGS = {
    "a", "b", "br", "center", "div", "em", "font", "h1", "h2", "h3", "h4",
    "h5", "h6", "header", "i", "img", "li", "ol", "p", "small", "span",
    "strong", "u", "ul"
}

# to generate "unique-ish" short strings to use for URL extentions
ALPHABET: str = string.ascii_lowercase + string.digits
CORNA_ROOT: pathlib.Path = pathlib.Path(__file__).parent.parent.parent
# Base API url for clients to call
UNVERSIONED_API_URL = "https://api.mycorna.com"


def respond_json_error(message: str, code: int) -> None:
    """Respond to a request with a JSON error message.

    :param str message: a description of the error condition
    :param int code: an HTTP error code
    """
    flask.abort(flask.make_response(flask.jsonify({'message': message}), code))


def get_uuid() -> str:
    """Get a random UUID.

    :returns: the UUID string
    :rtype: str
    """
    return str(uuid.uuid4())


def load_json(path: pathlib.Path | str) -> Optional[dict[str, Any]]:
    """Load json from a path.

    :param str path: the path to the json file
    :return: contents of json file or None
    :rtype: Optional[dict]
    """
    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    contents: Optional[dict[str, Any]] = None

    if not path.exists():
        logger.error("no path found at: '%s'", str(path))
        return contents

    if not path.is_file():
        logger.error("Path is not a valid file. Path: '%s'", str(path))
        return contents

    with open(path, "r", encoding="utf-8") as fd:
        try:
            contents = json.load(fd)
        except json.JSONDecodeError as e:
            logger.error("JSON Decode Error in file '%s': %s", str(path), e)

    return contents


def current_user(
    session: LocalProxy,
    cookie: str,
    exception: type = NotLoggedInError,
) -> models.UserTable:
    """Return the current user.

    This function returns an instance of the current user depending
    on the given cookie.

    :param LocalProxy session: a db session
    :param str cookie: a signed cookie
    :param type exception: Custom exception to raise on failure

    :return: a user object
    :rtype: models.UserTable
    :raises exception: if user is not logged in
    """
    cookie_id: str = secure.decoded_message(cookie)
    user_session: Optional[models.UserTable] = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .one_or_none()
    )

    if user_session is None:
        raise exception("User not logged in")

    return user_session.user


def login_required(func: Callable):
    """Login required decorator.

    :param Callable func: the function being wrapped.
    :returns: the wrapped function after the users login
        status has been checked
    :rtype: Callable
    """
    @wraps(func)
    def inner(*args, **kwargs):
        """Check user is logged in."""
        signed_cookie: Optional[str] = (
            flask
            .request
            .cookies
            .get(enums.SessionNames.SESSION.value)
        )

        if not signed_cookie or not secure.is_valid(signed_cookie):
            respond_json_error(
                "Login required for this action",
                HTTPStatus.UNAUTHORIZED,
            )

        return func(*args, **kwargs)
    return inner


# pylint: disable=raise-missing-from
def check_response(response, error_msg, exc_cls):
    """Call `raise_for_status` on `response`; log `error_msg` if necessary.

    Use this function to add nicer error messages to failed calls to
    `requests`, raising a custom exception rather than a `requests` exception.

    :param requests.models.Response response:
    :param str error_msg: a "nice" error message to be logged along side the
        exception raised by `raise_for_status`
    :param type exc_cls: an exception class
    :raises exc_cls: if the response contains an error code
    """
    # If we try to query the payload inside the raise_for_status try/except,
    # it will overwrite the exception info that logging.exception uses. So
    # we must construct this error message here even though we might not use
    # it.
    msg = f"{error_msg} ({response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        pass
    else:
        if isinstance(payload, dict):
            err = payload.get('message') or payload.get('messages')
        else:
            err = payload
        if err:
            msg += " - {err}"
    msg += ')'

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        logger.exception(msg)
        raise exc_cls(msg, request=error.request, response=error.response)


class DisableOptionsOperationPlugin(apispec.BasePlugin):
    """An apispec plugin to remove 'OPTIONS' endpoints from the docs.

    Source:
      https://github.com/jmcarp/flask-apispec/issues/155#issuecomment-562542538
    """

    def operation_helper(self, path=None, operations=None, **kwargs):
        operations.pop("options", None)


@lru_cache()
def copy_schema_with_missing_values_stripped(schema):
    """Create a copy of a schema, but removing 'missing' field values.

    This works recursively for nested schemas.

    :param marshmallow.Schema schema: the target schema
    :returns: a copy of `schema`, but with any 'missing' field values
        removed (the field remains)
    :rtype: marshmallow.Schema
    """
    # We must not create schemas with duplicate names
    new_schema_name = f"Rules{schema.__name__}"

    new_fields = {}
    items = schema._declared_fields.items()  # pylint: disable=protected-access
    for attribute, field in items:
        new_field = deepcopy(field)
        if isinstance(field, fields.Nested):
            new_nested = copy_schema_with_missing_values_stripped(
                field.nested
            )
            new_field.nested = new_nested

        new_field.missing = marshmallow_missing
        new_fields[attribute] = new_field

    new_schema = type(new_schema_name, (BaseSchema,), new_fields)
    return new_schema


def nested_dict_update(dest, other):
    """Update keys from nested dictionary.

    :param dict dest: The dictionary to update (will be changed in place)
    :param dict other: The data to update from
    :rtype: dict
    :returns: The updated dictionary

    From https://stackoverflow.com/a/3233356/104446
    """
    for key, value in other.items():
        if isinstance(value, collections.abc.Mapping):
            dest[key] = nested_dict_update(dest.get(key, {}), value)
        else:
            dest[key] = value
    return dest


def exists_(
    session: LocalProxy,
    table_column: models.Base,
    check_val: str
) -> bool:
    """Check if some value exists in a table

    :param sqlalchemy.Session session: a db session
    :param models.Table.column table_column: name of column to search on
        e.g. UserTable.email_address
    :param str check_val: the value to look for

    :return: True if value exists, else False
    :rtype: bool
    """
    # wrap this in a try and raise error
    return session.query(
        exists().where(table_column == check_val)
    ).scalar()


def random_short_string(length: int = 8) -> str:
    """Random-ish short string generator.

    :param int length: length of string
    :return: random-ish short string
    :rtype: str

    From: https://stackoverflow.com/q/13484726
    """
    return "".join(random.choices(ALPHABET, k=length))


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


def validate_files(
    files: List[FileStorage],
    minimum: int = None,
    maximum: int = None,
) -> None:
    """Ensure incoming files are valid."""

    if minimum and len(files) < minimum:
        respond_json_error(
            f"This URI expects at least {minimum} files",
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    if maximum and len(files) > maximum:
        respond_json_error(
            f"This URI expects no greater than {maximum} file(s)",
            HTTPStatus.UNPROCESSABLE_ENTITY
        )

    for file in files:
        if not is_allowed(file.filename):
            respond_json_error(
                "Illegal file type",
                HTTPStatus.UNPROCESSABLE_ENTITY
            )


def clean_html(html: str) -> str:
    """Clean incoming HTML sting.

    This is a custom wrapper around nh3.clean.

    :param str html: the html to clean
    :returns: cleaned HTML
    :rtype: str
    """
    def attribute_filter(tag: str, attr: str, value: str) -> str | None:
        """Ensure href and src URLs are valid.

        :param str tag: html tag
        :param str attr: html tag attribute
        :param str value: the attribute value
        :returns: the value if valid
        :rtype: str | None
        """
        if tag in ("a", "img") and attr in ("href", "src"):
            if not validators.url(value):
                logger.warning(
                    "Invalid URL found for tag '%s': '%s'", tag, value)
                return None

            # we only want images to come from our own url in posts created by
            # the user. They can post links to other website images but that
            # has to use anchor tags, not image tags. If they want to use an
            # image inline when making a post, the way our client functions is
            # such that, the image will first be uploaded to the server and
            # then the upload link will be used in the image tag.
            if tag == "img" and attr == "src":
                if not value.startswith(UNVERSIONED_API_URL):
                    logger.warning("Invalid image src URL: '%s'", value)
                    return None
        return value

    # pylint complains about ALLOWED_ATTRIBUTES and `clean()`, the both exist
    # so I dont know why thats happening.
    attributes = deepcopy(nh3.ALLOWED_ATTRIBUTES)  # pylint: disable=no-member
    # we allow users to edit the type face of their posts
    attributes["font"] = {"face", "size"}
    return nh3.clean(  # pylint: disable=no-member
        html,
        tags=ALLOWED_HTML_TAGS,
        attributes=attributes,
        attribute_filter=attribute_filter,
    )


def atomic_stream_write(
    blob: FileStorage | io.BytesIO,
    path: pathlib.Path,
    suffix: str = ".tmp",
) -> None:
    """Atomically write a steam like object to the filesystem.

    :param FileStorage blob: the blob to write
    :param pathlib.Path path: write path
    :param str suffix: the suffix to use for the temp file
    """
    # Overwrite-safe: write to temp then move
    tmp_path: pathlib.Path = path.with_suffix(suffix)
    # ensure we're back at the start
    blob.stream.seek(0)
    # to avoid any overwriting risks, we handle the saving ourselves rather
    # than using the built in`.save()` method.
    with open(tmp_path, "wb") as fd:
        # write 1mb of data at a time
        shutil.copyfileobj(blob.stream, fd, length=1024 * 1024)
    tmp_path.replace(path)


def atomic_text_write(path: pathlib.Path, text: str) -> None:
    """Atomically write text to a file.

    This is another on of those shoddy attempts at 'isolation' and 'atomicity'.
    It doesn't really stop race-conditions but does prevent two processes
    writing to the same file at the same time.

    Might be worth adding read lock on files that need atomicity :thinks:

    Note: This file does not update the pre-existing file, it overwrites it.
    Its up to the caller to handle data preservation.

    :param pathlib.Path path: write path
    :param str text: the text data to update the file with.
    """
    tmp: pathlib.Path = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def to_filestorage(
    stream_or_path: io.BytesIO | str,
    filename: str,
) -> FileStorage:
    """Covert a blob object or a file descriptor to a FileStorage object.

    :param io.BytesIO stream_or_path: either a stream like object or a path
        to a file to read into memory
    :param str filename: the desired filename of the resulting FileStorage obj
    :return: a FileStorage object containing the file data
    :rtype: FileStorage
    """
    # try and guess the mimetype from the filename. Fall back to
    # `application/octet-stream` for unknown files
    mimetype: str = (
        mimetypes.guess_type(filename, strict=False)[0]
        or "application/octet-stream"
    )

    fs: Optional[FileStorage] = None

    if isinstance(stream_or_path, io.BytesIO):
        fs = FileStorage(
            stream=stream_or_path, filename=filename, content_type=mimetype)

    else:

        with open(stream_or_path, "rb") as fd:
            file_content: bytes = fd.read()
            # FileStorage expects a stream like object which has a `read()`
            # method. So thats why we have to do this.
            file_stream = io.BytesIO(file_content)
            fs = FileStorage(
                stream=file_stream, filename=filename, content_type=mimetype)

    return fs
