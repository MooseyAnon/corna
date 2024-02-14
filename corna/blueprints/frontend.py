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


@frontend.route("/frontend/login", methods=["GET"])
def login_page():
    """Serve login page."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "login.html")


@frontend.route("/frontend/register", methods=["GET"])
def register_page():
    """Server registration page."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "signup.html")


@frontend.route("/frontend/editor", methods=["GET"])
def editor():
    """Serve rich text editor."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "editor.html")


@frontend.route("/frontend/createButton", methods=["GET"])
def create_button():
    """Serve create post button."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "createButton.html")


@frontend.route("/frontend/loginButton", methods=["GET"])
def login_button():
    """Serve create post button."""
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "loginButton.html")


@frontend.route("/frontend/static/<path:path>", methods=["GET"])
def get_static(path):
    """Serve static files.

    Note: this is only used during local development, not in production.

    :param str path: the path to the static file.
    """
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public"), path)
