"""Utilities for `corna`."""

import collections.abc
from copy import deepcopy
from functools import lru_cache, wraps
from http import HTTPStatus
import logging
import pathlib
import random
import string
from typing import Callable, Optional
import uuid

import apispec
import flask
from marshmallow import fields, missing as marshmallow_missing
import requests
from sqlalchemy import exists
from werkzeug.local import LocalProxy

from corna import enums
from corna.controls.marshmallow_control import BaseSchema
from corna.db import models
from corna.utils import secure
from corna.utils.errors import NotLoggedInError

logger = logging.getLogger(__name__)

# to generate "unique-ish" short strings to use for URL extentions
ALPHABET: str = string.ascii_lowercase + string.digits
CORNA_ROOT: pathlib.Path = pathlib.Path(__file__).parent.parent.parent


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
        signed_cookie: Optional[str] = flask.request.cookies.get(
            enums.SessionNames.SESSION.value)

        if not signed_cookie or not secure.is_valid(signed_cookie):
            respond_json_error(
                "Login required for this action",
                HTTPStatus.BAD_REQUEST
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
