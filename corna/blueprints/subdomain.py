"""The code in this file directly deals with all <subdomain> related activity.

This means:
    - user homepage
    - single post page
    - contents of single post as a fragment
    - search by keyword/tag


Fragments are stand alone HTML blocks that represent a single post. They can be
used on the frontend with AJAX.

Fragments are distinct from anything the API endpoints will return. The API's
will only ever return the JSON representation of the post.
"""
import pathlib
from typing import Optional

import flask

from corna import enums
from corna.controls import subdomain_control as control
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import secure, utils

THEME_DIR: pathlib.Path = utils.CORNA_ROOT / "themes"
subdomain = flask.Blueprint("subdomain", __name__, template_folder=THEME_DIR)


@subdomain.after_request
def sec_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    """Add security headers to every response.

    :param flask.Response response:
    :returns: flask response object with updated headers
    :rtype: flask.Response
    """
    headers = secure.secure_headers(flask.request)
    response.headers.update(headers)
    return response


@subdomain.route("/subdomain/<domain>", methods=["GET"])
def user_homepage(domain):
    """Serve user homepage."""
    signed_cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )
    post_list, title, theme_path = control.build_page(
        session,
        domain,
        cookie=signed_cookie,
    )
    return flask.render_template(
        theme_path,
        PostList=post_list,
        title=title
    )


@subdomain.route("/subdomain/<dom_name>/fragment/<url_ext>", methods=["GET"])
def get_fragment(dom_name, url_ext):
    """Serve a single post as HTML fragment."""
    signed_cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )
    post = control.single_post(
        session,
        url_ext,
        dom_name,
        cookie=signed_cookie,
    )
    return flask.jsonify(post)


@subdomain.route("/subdomain/static/<path:path>", methods=["GET"])
def get_static(path):
    """Serve static files.

    Note: this is only used during local development, not in production.

    :param str path: the path to the static file.
    """
    return flask.send_from_directory(THEME_DIR, path)
