"""Theme management endpoints."""

from http import HTTPStatus
from typing import Dict, Optional

import flask

from corna import enums
from corna.utils import secure, utils

themes = flask.Blueprint("themes", __name__)


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
