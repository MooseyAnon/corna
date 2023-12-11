"""Frontend for Corna.

This file mostly deals with sending the HTML files for our frontend.
It also handles static files for _local_ development. In production nginx
will handle serving static files.
"""

import flask

from corna.utils import utils

frontend = flask.Blueprint("frontend", __name__)


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


@frontend.route("/frontend/static/<path:path>", methods=["GET"])
def get_static(path):
    """Serve static files.

    Note: this is only used during local development, not in production.

    :param str path: the path to the static file.
    """
    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public"), path)
