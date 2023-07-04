"""Utilities for `corna`."""

import datetime
import logging
import pathlib
import uuid

import flask

logger = logging.getLogger(__name__)


def respond_json_error(message: str, code: int) -> None:
    """Respond to a request with a JSON error message.

    :param str message: a description of the error condition
    :param int code: an HTTP error code
    """
    flask.abort(flask.make_response(flask.jsonify({'message': message}), code))


def get_utc_now() -> datetime.datetime:
    """Get a time-zone aware datetime for "now".

    :returns: "now" as a datetime
    :rtype: datetime.datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def get_uuid() -> str:
    """Get a random UUID.

    :returns: the UUID string
    :rtype: str
    """
    return str(uuid.uuid4())


def mkdir(path: pathlib.Path) -> None:
    """Recursively make directories in a path.

    Note: this is only here to make logging a bit cleaner.

    :param pathlib.Path path: path or directory to make
    """
    if not isinstance(path, pathlib.Path):
        logger.warning(
            "path must a pathlib.Path object, attempting to convert"
        )
        path: pathlib.Path = pathlib.Path(path)

    # recursively make path
    path.mkdir(parents=True, exist_ok=True)
