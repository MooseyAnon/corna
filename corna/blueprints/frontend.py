"""Frontend for Corna.

This file mostly deals with sending the HTML files for our frontend.
It also handles static files for _local_ development. In production nginx
will handle serving static files.
"""
import logging

import flask

from corna.utils import secure, utils

logger = logging.getLogger(__name__)

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


@frontend.route("/frontend", methods=["GET"])
def neighbourhoods():
    """Corna homepage."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "neighbourhoods.html")


@frontend.route("/frontend/nav", methods=["GET"])
def nav():
    """Serve create post button."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "nav-test.html")


@frontend.route("/frontend/cornaCore", methods=["GET"])
def corna_core():
    """Serve create post button."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "cornaCore.html")


@frontend.route("/frontend/cornaCore/<path:path>", methods=["GET"])
def text_modal(path):
    """Serve create post button."""
    full_path = f"{path}.html"
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), full_path)


@frontend.route("/frontend/static/<path:path>", methods=["GET"])
def get_static(path):
    """Serve static files.

    Note: this is only used during local development, not in production.

    :param str path: the path to the static file.
    """
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public"), path)
