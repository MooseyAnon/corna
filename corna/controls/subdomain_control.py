"""Control code for a users Corna client experience."""

import logging
from typing import Dict, List, Optional, Tuple, Union

from markupsafe import Markup
from werkzeug.local import LocalProxy

from corna import enums
from corna.db import models
from corna.utils import utils

logger = logging.getLogger(__name__)


class CornaNotFoundError(ValueError):
    """No Corna exists for the given subdomain."""


class PostNotFoundError(ValueError):
    """Post not found."""


def _current_corna(session: LocalProxy, subdomain: str) -> models.CornaTable:
    """Get Corna details for a given subdomain.

    :param LocalProxy session: db session
    :param str subdomain: the Corna subdomain

    :returns: Corna information associated with the subdomain
    :rtype: model.Corna
    :raises CornaNotFoundError: if there is no corna for subdomain
    """
    corna: Optional[models.CornaTable] = (
        session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == subdomain)
        .one_or_none()
    )

    if not corna:
        logger.warning("No corna names %s found", subdomain)
        raise CornaNotFoundError(
            f"No Corna with the domain {subdomain} found.")

    return corna


def _post_title(post: models.PostTable) -> str:
    """Get the post title.

    Titles are optional so this function does some checks.

    :params models.PostTable post: a single post
    :returns: title is post has a title
    :rtype: Optional[str]
    """
    title: Optional[str] = (
        post.text.title
        if (post.text and post.text.title)
        else None
    )
    return title


def _post_html_fragment(post: models.PostTable) -> str:
    """Get post contents as HTML.

    :param models.PostTable post: a single post
    :returns: post content as HTML
    :rtype: Optional[str]
    """

    html_content: Optional[str] = (
        Markup(post.text.inner_html)
        if (post.text and post.text.inner_html)
        else None
    )
    return html_content


def _image_api_href(url_extension: str) -> str:
    """Return full image download URL.

    :param str url_extension: the URL extension for the image
    :returns: full download URL for image
    :rtype: str
    """
    href: str = f"{utils.UNVERSIONED_API_URL}/v1/media/download/{url_extension}"
    return href


def _parse_post(
    post: models.PostTable,
    subdomain: str
) -> Dict[str, Union[List[str], str]]:
    """Parse a given post.

    :param models.PostTable post: a single post
    :param str subdomain: the subdomain for the corna
    :returns: post parsed with core details extracted
    :rtype: Dict[str, str]
    """
    content: Dict[str, Union[List, str]] = {
        "uuid": post.uuid,
        "href": post.url_extension,
        "created": post.created.isoformat(),
        "type": post.type,
        "domain_name": subdomain,
        "title": _post_title(post),
    }

    content_key: str = (
        "content"
        if post.type == enums.ContentType.TEXT
        else "caption"
    )
    content.update({content_key: _post_html_fragment(post)})

    if post.type == enums.ContentType.PHOTO or len(post.images) > 0:
        images: List[str] = [
            _image_api_href(image.url_extension)
            for image in post.images
        ]
        content.update({"images": images})

    return content


def post_list(
    session: LocalProxy,
    subdomain: str
) -> List[Dict[str, Union[List[str], str]]]:
    """Get the post list for a given domain.

    :param LocalProxy session: a db session
    :param str subdomain: the Corna to get posts from
    :returns: a post list for a given Corna
    :rtype: Dict[str, str]
    """
    curr_corna: Optional[models.CornaTable] = _current_corna(session, subdomain)

    posts: List[Optional[models.PostTable]] = (
        session
        .query(models.PostTable)
        .filter(models.PostTable.corna_uuid == curr_corna.uuid)
        # We're disabling pylints (singleton-comparison) check because
        # in sqlalchemy equality checking against the boolean is actually
        # important for the generated SQL statement. Its not a python-land
        # thing.
        .filter(models.PostTable.deleted == False)  # pylint: disable=C0121
        .all()
    )
    parsed_posts: List[Dict[str, Union[List[str], str]]] = [
        _parse_post(post, subdomain)
        for post in posts
    ]
    return parsed_posts


def single_post(
    session: LocalProxy,
    url_extension: str,
    subdomain: str
) -> Dict[str, Union[List[str], str]]:
    """Get a single post.

    :param LocalProxy session: a db session
    :param str url_extension: url extension of post
    :param str subdomain: the Corna the post lives on

    :returns: a parsed post
    :rype: Dict[str, Union[List[str], str]]
    :raises PostNotFoundError: if no post is found
    """
    corna: Optional[models.CornaTable] = _current_corna(session, subdomain)
    post: Optional[models.PostTable] = (
        session
        .query(models.PostTable)
        .filter(models.PostTable.url_extension == url_extension)
        .one_or_none()
    )

    if not post or post.deleted is True or post.corna_uuid != corna.uuid:
        logger.warning(
            "post with extension %s does not exist on corna with domain %s",
            url_extension,
            subdomain,
        )
        raise PostNotFoundError("Post does not exist.")

    return _parse_post(post, subdomain)


def corna_title(session: LocalProxy, subdomain: str) -> Optional[str]:
    """Get the title of a Corna.

    :param LocalProxy session: a db session
    :param str subdomain: Corna subdomain
    :returns: title
    :rtype: Optional[str]
    """
    curr_corna: Optional[models.CornaTable] = _current_corna(
        session, subdomain)

    title = (
        curr_corna.title
        if (curr_corna and curr_corna.title)
        else None
    )
    return title


def theme(session: LocalProxy, subdomain: str) -> str:
    """Get Corna theme.

    :param LocalProxy session: db session
    :param str subdomain: Corna subdomain
    :returns: path to theme
    :rtype: str
    :raises ValueError: if no theme is found
    """
    curr_corna: Optional[models.CornaTable] = _current_corna(
        session, subdomain
    )
    theme_: Optional[models.Themes] = (
        session
        .query(models.Themes)
        .filter(models.Themes.uuid == curr_corna.theme)
        .one_or_none()
    )

    if not theme_:
        raise ValueError("No theme found for Corna")

    return theme_.path


def build_page(
    session: LocalProxy,
    subdomain: str
) -> Tuple[List[Dict[str, Union[List[str]]]], str, str]:
    """Build page for Corna.

    :param LocalProxy session: db session
    :param str subdomain: Corna subdomain
    :returns: all components needed to build a Corna
    :rtype: Tuple[post_list, str, str]
    """
    posts = post_list(session, subdomain)
    title = corna_title(session, subdomain)
    theme_path = theme(session, subdomain)

    return posts, title, theme_path
