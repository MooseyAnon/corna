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
import logging
import pathlib
from typing import Optional

import flask

from corna import enums
from corna.controls import subdomain_control as control
from corna.oss.flask_sqlalchemy_session import current_session as session
from corna.utils import errors, secure, utils

logger = logging.getLogger(__name__)

THEME_DIR: pathlib.Path = utils.CORNA_ROOT / "themes"
subdomain = flask.Blueprint("subdomain", __name__, template_folder=THEME_DIR)


def get_cookie() -> Optional[str]:
    """Get signed user cookie, if available.

    :returns: signed cookie if user is logged in.
    :rtype: Optional[str]
    """
    cookie: Optional[str] = (
        flask
        .request
        .cookies
        .get(enums.SessionNames.SESSION.value)
    )

    return cookie


def render_system_error(message):
    """Fallback system error for when we can't display theme errors.

    :param str message: the error message.
    """
    return flask.render_template("system-error.html", message=message)


def render_theme_error(domain_name, message, page):
    """Render a theme error.

    Note: in the weird scenario that a theme does not exist, we fallback
    to the system error.

    :param str domain_name: the corna we care about
    :param str message: the error message to display
    :param str page: the theme error page to fetch. Each page may have a custom
        error or theme may opt to return a generic theme error. This is
        abstracted away.
    """
    error_path = control.get_error_page(session, domain_name, page)
    if not error_path:
        return render_system_error(message)

    return flask.render_template(
        str(error_path), success=False, message=message)


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
    signed_cookie: Optional[str] = get_cookie()

    try:
        page = control.build_page(
            session,
            domain,
            cookie=signed_cookie,
        )

    except errors.UnauthorizedActionError:
        msg = "You do not have permission to see this page, sorry."
        return render_theme_error(domain, msg, page="homepage"), 403
    # this means this is not a valid domain name. Thus there is no chance
    # of finding a valid theme error, so we need to fall back onto the system
    # error page
    except control.CornaNotFoundError:
        msg = "Oops, seems like there is nothing here :("
        return render_system_error(msg), 400
    # value error is raised if there is no theme for the corna. This means
    # we need to fallback onto the system error.
    except ValueError:
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500
    # catchall fallback as we never want users to see the basic flask error
    # page
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Caught unexpected error: %s", e)
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500

    return flask.render_template(
        str(page.theme_path),
        # I dont like this design might change it
        success=True,
        listing=page.listing,
        title=page.title
    )


@subdomain.route("/subdomain/<domain>/p/<url_ext>", methods=["GET"])
def single_post_page(domain, url_ext):
    """Serve a single post page."""
    signed_cookie: Optional[str] = get_cookie()

    try:
        post, theme = control.single_post(
            session,
            url_ext,
            domain,
            cookie=signed_cookie,
        )

    except errors.UnauthorizedActionError:
        msg = "You do not have permission to see this page, sorry."
        return render_theme_error(domain, msg, page="post_page"), 403

    except control.PostNotFoundError:
        msg = "Oops, seems like there is nothing here :("
        return render_theme_error(domain, msg, page="post.html"), 404
    # this means this is not a valid domain name. Thus there is no chance
    # of finding a valid theme error, so we need to fall back onto the system
    # error page
    except control.CornaNotFoundError:
        msg = "Oops, seems like there is nothing here :("
        return render_system_error(msg), 400
    # value error is raised if there is no theme for the corna. This means
    # we need to fallback onto the system error.
    except ValueError:
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500
    # catchall fallback as we never want users to see the basic flask error
    # page
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Caught unexpected error: %s", e)
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500

    return flask.render_template(
        str(theme),
        # I dont like this design might change it
        success=True,
        post=post,
    )


@subdomain.route("/subdomain/<domain>/about", methods=["GET"])
def about_page(domain):
    """Get about page for a corna."""
    signed_cookie: Optional[str] = get_cookie()

    try:
        about_data = control.about(
            session,
            domain,
            cookie=signed_cookie
        )

    except errors.UnauthorizedActionError:
        msg = "You do not have permission to see this page, sorry."
        return render_theme_error(domain, msg, page="about"), 403
    # this means this is not a valid domain name. Thus there is no chance
    # of finding a valid theme error, so we need to fall back onto the system
    # error page
    except control.CornaNotFoundError:
        msg = "Oops, seems like there is nothing here :("
        return render_system_error(msg), 400
    # value error is raised if there is no theme for the corna. This means
    # we need to fallback onto the system error.
    except ValueError:
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500
    # catchall fallback as we never want users to see the basic flask error
    # page
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Caught unexpected error: %s", e)
        msg = "Excuse us, something went horribly wrong!"
        return render_system_error(msg), 500

    return flask.render_template(
        str(about_data.theme_path),
        # I dont like this design might change it
        success=True,
        cornaTitle=about_data.title,
        owner=about_data.owner,
        about=about_data.about,
        avatar_url=about_data.avatar_url,
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


@subdomain.route("/subdomain/<domain>/<path:path>", methods=["GET"])
def catch_all_error(domain, path):  # pylint: disable=unused-argument
    """Catch all error on subdomain."""
    msg = "Oops, seems like there is nothing here :("
    return render_theme_error(domain, msg, page="default"), 404
