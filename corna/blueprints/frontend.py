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
    # We dont want to render this page unless its made from the iframe
    # so we've added a little flag which checks. There is no security
    # threat if this gets directly loaded in the browser, its just ugly.
    mode = flask.request.args.get("mode")
    if mode != "fragment":
        error_msg = "Oops, nothing to see here!"
        return flask.render_template(
            "system-error.html", message=error_msg), 404

    return flask.send_from_directory(
        (utils.CORNA_ROOT / "frontend/public/html"), "nav-test.html")


@frontend.route("/frontend/cornaCore/<path:path>", methods=["GET"])
def text_modal(path):
    """Serve create post button."""
    # we only want to return requests from HTMX
    if flask.request.headers.get("HX-Request") != "true":
        error_msg = "Oops, nothing to see here!"
        return flask.render_template(
            "system-error.html", message=error_msg), 404

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


@frontend.route("/frontend/<path:path>", methods=["GET"])
def catch_all_error(path):  # pylint: disable=unused-argument
    """Catch unknown frontend routes and return a themed error page.."""
    error_msg = "Oops, seems like there is nothing here :("
    return flask.render_template("system-error.html", message=error_msg), 404
