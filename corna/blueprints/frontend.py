"""Frontend for Corna.

This file mostly deals with sending the HTML files for our frontend.
It also handles static files for _local_ development. In production nginx
will handle serving static files.
"""
import logging

import flask

from corna import enums
from corna.db import models
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import get_utc_now, secure, utils

logger = logging.getLogger(__name__)

frontend = flask.Blueprint("frontend", __name__)


def handle_intent(intent: str) -> dict[str, str]:
    """Format request intent.

    :param str intent: the user intent
    :return: formatted intent for the client
    """
    intent_bootstrap = {"intent": intent}
    return intent_bootstrap


def is_loggedin() -> bool:
    """Check if incoming request is authenticated.

    :returns: true if request is a valid session i.e. user logged in,
        else false
    :rtype: bool
    """
    signed_cookie: str | None = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )

    return signed_cookie and secure.is_valid(signed_cookie)


def is_valid_token(session_, token: str) -> bool:
    """Validate user registration token.

    The reason we dont use the validation function in `auth_control.py` is
    because that function locks the invite table row. We really dont need to
    do that for a light validation step. The main registration path will
    correctly validate it anyways.

    :param LocalProxy session_: db connection
    :param str token: the invite token
    :returns: true if token is valid, else false
    :rtype: bool
    """

    try:
        token_hash: str = secure.hash_invite_token(token)
    except ValueError:
        return False

    # we dont actually save the raw token string (it only gets shown once on
    # the out path) so we need to search using the token hash - which we do
    # have
    invite: models.InviteTable | None = (
        session_
        .query(models.InviteTable)
        .filter(models.InviteTable.token_hash == token_hash)
        .one_or_none()
    )

    now = get_utc_now()
    if (
        invite is None
        or invite.redeemed_at is not None
        or invite.revoked_at is not None
        or invite.expires_at <= now
    ):
        return False

    return True


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


@frontend.route("/frontend/post/video", methods=["GET"])
def video_post_page():
    """Create video post page."""
    # we only want people going to this page is they're logged in
    # if not, we'll just send them to sign in page
    if not is_loggedin():
        return flask.render_template(
            "neighbourhoods.html", bootstrap=handle_intent("signin"))

    return flask.render_template(
        "neighbourhoods.html", bootstrap=handle_intent("post:video"))


@frontend.route("/frontend/post/image", methods=["GET"])
def image_post_page():
    """Create image post page."""
    # we only want people going to this page is they're logged in
    # if not, we'll just send them to sign in page
    if not is_loggedin():
        return flask.render_template(
            "neighbourhoods.html", bootstrap=handle_intent("signin"))

    return flask.render_template(
        "neighbourhoods.html", bootstrap=handle_intent("post:image"))


@frontend.route("/frontend/post/text", methods=["GET"])
def text_post_page():
    """Create text post page."""
    # we only want people going to this page is they're logged in
    # if not, we'll just send them to sign in page
    if not is_loggedin():
        return flask.render_template(
            "neighbourhoods.html", bootstrap=handle_intent("signin"))

    return flask.render_template(
        "neighbourhoods.html", bootstrap=handle_intent("post:text"))


@frontend.route("/frontend/join/<token>", methods=["GET"])
def join_request(token: str):
    """Handle an incoming join request."""
    # nothing to do if the user is already logged in
    if is_loggedin():
        return flask.render_template("neighbourhoods.html", bootstrap=None)

    payload = {
        "token": token,
        "is_valid": True,
        "message": "Thanks for choosing to signup to Corna!",
    }

    if not is_valid_token(session, token):
        payload["is_valid"] = False
        payload["message"] = "Invite token is invalid or expired."

    bootstrap = handle_intent("join")
    bootstrap.update({"payload": payload})
    return flask.render_template("neighbourhoods.html", bootstrap=bootstrap)


@frontend.route("/frontend/invite", methods=["GET"])
def invite_user_in_page():
    """Page for users generating invite URLS."""
    # direct user to sign in page if not logged in
    intent = "signin" if not is_loggedin() else "invite"
    bootstrap = handle_intent(intent)
    return flask.render_template("neighbourhoods.html", bootstrap=bootstrap)


@frontend.route("/frontend/signin", methods=["GET"])
def sign_in_page():
    """Sign-in page."""
    # if the user is already logged in, there is nothing to do
    bootstrap = handle_intent("signin") if not is_loggedin() else None
    return flask.render_template("neighbourhoods.html", bootstrap=bootstrap)


@frontend.route("/frontend", methods=["GET"])
def neighbourhoods():
    """Corna homepage."""
    return flask.render_template("neighbourhoods.html")


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
