"""Frontend for Corna.

This file mostly deals with sending the HTML files for our frontend.
It also handles static files for _local_ development. In production nginx
will handle serving static files.
"""

import flask

from corna.utils import secure, utils

frontend = flask.Blueprint("frontend", __name__)


@frontend.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response:
    :returns: flask response object with updated headers
    :rtype: flask.Response
    """
    headers = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


    return flask.send_from_directory(


    return flask.send_from_directory(


    """Serve create post button."""
    return flask.send_from_directory(


    """Serve create post button."""
    return flask.send_from_directory(


@frontend.route("/frontend/static/<path:path>", methods=["GET"])
def get_static(path):
    """Serve static files.

    Note: this is only used during local development, not in production.

    :param str path: the path to the static file.
    """
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public"), path)
