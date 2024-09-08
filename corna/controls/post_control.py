"""Manage Corna posts."""

import logging
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy.orm.scoping import scoped_session as Session
from typing_extensions import TypedDict

from corna.db import models
from corna.enums import ContentType
from corna.middleware import alchemy, check
from corna.utils import get_utc_now, secure, utils
from corna.utils.errors import UnauthorizedActionError
from corna.utils.utils import current_user

logger = logging.Logger(__name__)


POST_TYPES: Tuple[str, ...] = tuple(
    post_type.value
    for post_type in ContentType
)


class InvalidContentType(ValueError):
    """Content type is not valid."""


class PostDoesNotExist(ValueError):
    """Post does not exit."""


# **** types ****

class Post(TypedDict):
    """Shared Across all posts."""

    type: str
    created: str
    post_url: str


class _TextPostRequired(Post):
    """Required on text posts."""

    content: str


class TextPost(_TextPostRequired, total=False):
    """Text post specific type."""

    title: str
    image_urls: List[str]
    inner_html: str
    uploaded_images: List[str]


class _ImagePostRquired(Post):
    """Required on image posts."""

    image_urls: List[str]


class ImagePost(_ImagePostRquired, total=False):
    """Image post type."""

    caption: str
    title: str


PostCollection = Union[TextPost, ImagePost]

# **** types end ****


def create(
    session: Session,
    cookie: str,
    domain_name: str,
    type: str,  # pylint: disable=redefined-builtin
    uploaded_images: List[str],
    content: Optional[str] = None,
    inner_html: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """Create a new corna post.

    :param Session session: a db session
    :param str cookie: user cookie
    :param str domain_name: corna domain name
    :param str type: type of post
    :param List[str] uploaded_images: a list of image slugs, that have already
        been uploaded to the server, which are a part of the post e.g. header
        image. Note: can be empty if post has no images.
    :param Optional[str] content: the text based content of the post. This
        is just the raw words (if any) of the post. This is not used for
        displaying content but rather saved for recommendation and indexing.
    :param Optional[str] inner_html: the HTML representation of the text
        content of the post. This is actually what is used to display the text
        on the client.
    :param Optional[str] title: the title of the post

    :raises InvalidContentType: if the incoming content type
        is not correct.
    :raises UnauthorizedActionError: is author is not authorized to
        create post.
    """
    user: models.UserTable = current_user(session, cookie)
    corna: models.CornaTable = alchemy.corna(session, domain_name)

    if not check.can_write(session, domain_name, user.username):
        raise UnauthorizedActionError("User unauthorized to create posts")

    if type not in POST_TYPES:
        raise InvalidContentType(f"{type} is not a valid type of content")

    url: str = secure.generate_unique_token(
        session=session,
        column=models.PostTable.url_extension,
        func=utils.random_short_string
    )
    post_uuid: str = utils.get_uuid()

    session.add(
        models.PostTable(
            deleted=False,
            url_extension=url,
            type=type,
            uuid=post_uuid,
            corna_uuid=corna.uuid,
            created=get_utc_now(),
            user_uuid=user.uuid,
        )
    )

    _create_artefacts(
        session,
        post_uuid=post_uuid,
        post_type=type,
        title=title,
        text_content=content,
        html=inner_html,
        uploaded_images=uploaded_images,
    )

    logger.info("successfully added new post!")


def _create_artefacts(
    session: Session,
    post_uuid: str,
    post_type: str,
    uploaded_images: List[str],
    title: Optional[str] = None,
    text_content: Optional[str] = None,
    html: Optional[str] = None,
) -> None:
    """Create individual post artefacts.

    This function is delegated the responsibility of creating the
    actual objects which make up the post. This allows us to do
    more thorough checks before saving.

    :param Session session: db session
    :param str post_uuid: the post UUID
    :param str post_type: the type of post
    :param List[str] uploaded_images: a list of image slugs, that have already
        been uploaded to the server, which are a part of the post e.g. header
        image. Note: can be empty if post has no images.
    :param Optional[str] content: the text based content of the post. This
        is just the raw words (if any) of the post. This is not used for
        displaying content but rather saved for recommendation and indexing.
    :param Optional[str] html: the HTML representation of the text content of
        the post. This is actually what is used to display the text on the
        client.
    :param Optional[str] title: the title of the post

    :raises InvalidContentType: if data does not contain required
        fields.
    """
    if post_type == ContentType.TEXT and not text_content:
        raise InvalidContentType("Text post needs text")

    if post_type == ContentType.PHOTO and not uploaded_images:
        raise InvalidContentType("Photo post needs images")

    # save text content, if any
    text(
        session,
        html=html,
        title=title,
        content=text_content,
        post_uuid=post_uuid,
    )

    # link any preloaded images
    link(
        session=session,
        post_uuid=post_uuid,
        uploaded_images=uploaded_images,
    )


def text(
    session: Session,
    post_uuid: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    html: Optional[str] = None,
) -> None:
    """Save textual information associated with a post.

    This is an optimistic function from the perspective of the
    caller as it only saves if there is actually anything to save.

    :param Session session: db session
    :param str post_uuid: the post UUID
    :param Optional[str] content: the text based content of the post. This
        is just the raw words (if any) of the post. This is not used for
        displaying content but rather saved for recommendation and indexing.
    :param Optional[str] html: the HTML representation of the text content of
        the post. This is actually what is used to display the text on the
        client.
    :param Optional[str] title: the title of the post
    """
    if not title and not content:
        return

    session.add(
        models.TextContent(
            post_uuid=post_uuid,
            uuid=utils.get_uuid(),
            title=title,
            content=content,
            inner_html=html,
            created=get_utc_now(),
        )
    )


def link(
    session: Session,
    post_uuid: str,
    uploaded_images: List[str] = None,
) -> None:
    """Link preloaded media to a new post.

    There are cases where we want to link pre-loaded, orphaned images
    to a post.

    :param Session session: db session
    :param str post_uuid: The uuid of the post to link to i.e. parent post
    :param List[str] uploaded_images: a list of url_extensions pointing to
        orphaned images already existing in the database.

    :raises PostDoesNotExist: if no image associated with the url exists
    """
    if not uploaded_images:
        return

    for url_extension in uploaded_images:
        image: Optional[models.Images] = (
            session
            .query(models.Media)
            .filter(models.Media.url_extension == url_extension)
            .one_or_none()
        )

        if not image or (image.orphaned is not True):
            raise PostDoesNotExist("Unable to find file")

        image.post_uuid = post_uuid
        image.orphaned = False


def get(
    session: Session,
    domain_name: str
) -> Dict[str, List[PostCollection]]:
    """Get all posts for a given corna.

    :param sqlalchemy.Session session: a db session
    :param str domain_name: the domain name of the corna

    :return: all the posts for a given corna
    :rtype: dict
    """
    corna: models.CornaTable = alchemy.corna(session, domain_name)

    posts: List[models.PostTable] = (
        session.
        query(models.PostTable)
        .filter(models.PostTable.corna_uuid == corna.uuid)
    )

    return {"posts": [_parse_post(post) for post in posts]}


def _parse_post(post: models.PostTable) -> PostCollection:
    """Correctly parse the out going post.

    :param models.PostTable post: a row from the database
    :return: a dict with the required fields
    :rtype: dict
    :raises InvalidContentType: if post type is unrecognised
    """
    if post.type == ContentType.TEXT:
        return _construct_text_post(post)
    if post.type == ContentType.PHOTO:
        return _construct_image_post(post)
    raise InvalidContentType("Unrecognised content Type")


def _construct_text_post(post: models.PostTable) -> TextPost:
    """Construct a text post.

    Takes a post object and returns the data expected by the API.

    :param models.PostTable post: a post object
    :returns: post information for the caller.
    :rtype: TextPost
    """
    domain_name: str = post.corna.domain_name
    post_url: str = build_url(post.url_extension, domain_name, post.type)

    parsed_post: TextPost = {
        "type": post.type,
        "created": post.created.isoformat(),
        "post_url": post_url,
        "content": post.text.content,
    }

    if post.text.title:
        parsed_post["title"] = post.text.title

    if post.images:
        url_list: List[str] = [
            build_url(image.url_extension, domain_name, "image")
            for image in post.images
        ]
        parsed_post["image_urls"] = url_list

    return parsed_post


def _construct_image_post(post: models.PostTable) -> ImagePost:
    """Construct an image post.

    Takes a post object and returns the data expected by the API.

    :param models.PostTable post: a post object
    :returns: formatted post data
    :rtype: ImagePost
    """
    domain_name: str = post.corna.domain_name
    post_url: str = build_url(post.url_extension, domain_name, post.type)
    url_list: List[str] = [
        build_url(image.url_extension, domain_name, "image")
        for image in post.images
    ]

    parsed_post: ImagePost = {
        "type": post.type,
        "created": post.created.isoformat(),
        "post_url": post_url,
        "image_urls": url_list
    }

    if post.text:
        if post.text.title:
            parsed_post["title"] = post.text.title

        if post.text.content:
            parsed_post["caption"] = post.text.content

    return parsed_post


def build_url(extension: str, domain_name: str, type_: str) -> str:
    """Build API url for posts and images.

    :param str extension: the unique url extension
    :param str domain_name: Corna domain name
    :param str type_: type of post
    :returns: full url
    :rtype: str
    """
    base: str = "https://api.mycorna.com/v1/posts"
    url: str = f"{base}/{domain_name}/{type_}/{extension}"
    return url
