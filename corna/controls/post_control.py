"""Manage Corna posts."""

import logging
import os
from typing import Dict, List, Optional, Tuple, Union

from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage
from werkzeug.local import LocalProxy

from corna.db import models
from corna.enums import ContentType
from corna.utils import get_utc_now, image_proc, secure, utils
from corna.utils.errors import CornaOwnerError
from corna.utils.utils import current_user

logger = logging.Logger(__name__)


POST_TYPES: Tuple[str, ...] = tuple(
    post_type.value
    for post_type in ContentType
)


class NoneExistinCornaError(ValueError):
    """Blog does not exists."""


class InvalidContentType(ValueError):
    """Content type is not valid."""


class PostDoesNotExist(ValueError):
    """Post does not exit."""


# **** types ****

class _TypesBase(TypedDict):
    """Shared Type."""

    type: str
    domain_name: str
    cookie: str


class _TextContentRequired(_TypesBase):
    """Required on text content."""

    content: str


class TextContent(_TextContentRequired, total=False):
    """Text content type."""

    title: str


class _ImagesRequired(_TypesBase):
    """Required on images."""

    images: List[FileStorage]


class ImagesUpload(_ImagesRequired, total=False):
    """Image type."""

    title: str
    caption: str


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


class _ImagePostRquired(Post):
    """Required on image posts."""

    image_urls: List[str]


class ImagePost(_ImagePostRquired, total=False):
    """Image post type."""

    caption: str
    title: str


CreatePostCollection = Union[TextContent, ImagesUpload]
PostCollection = Union[TextPost, ImagePost]

# **** types end ****


def get_corna(session: LocalProxy, domain_name: str) -> models.CornaTable:
    """Get the Corna associated with the given domain.

    :param LocalProxy session: db session
    :param str domain_name: domain to look up

    :returns: the Corna with the given domain
    :rtype: models.CornaTable
    :raises NoneExistinCornaError: if there is no Corna
    """

    corna: Optional[models.CornaTable] = (
        session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == domain_name)
        .one_or_none()
    )

    if corna is None:
        raise NoneExistinCornaError("corna does not exist")

    return corna


def create(session: LocalProxy, data: CreatePostCollection) -> None:
    """Create a new corna post.

    :param sqlalchemy.Session session: a db session
    :param CreatePostCollectione data: the incoming data to be saved
    :raises CornaOwnerError: user does not own the corna
    :raises InvalidContentType: if the incoming content type
        is not correct.
    """
    user: models.UserTable = current_user(session, data["cookie"])
    corna: models.CornaTable = get_corna(session, data["domain_name"])
    type_: str = data["type"]

    if not user.uuid == corna.user_uuid:
        raise CornaOwnerError("Current user does not own the Corna")

    if type_ not in POST_TYPES:
        raise InvalidContentType(f"{type_} is not a valid type of content")

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
            type=type_,
            uuid=post_uuid,
            corna_uuid=corna.uuid,
            created=get_utc_now(),
        )
    )

    _creat_artefacts(session, post_uuid, data)

    logger.info("successfully added new post!")


def _creat_artefacts(
    session: LocalProxy,
    post_uuid: str,
    data: CreatePostCollection
) -> None:
    """Create individual post artefacts.

    This function is delegated the responsibility of creating the
    actual objects which make up the post. This allows us to do
    more thorough checks before saving.

    :param LocalProxy session: db session
    :param CreatePostCollection data: incoming data
    :raises InvalidContentType: if data does not contain required
        fields.
    """
    post_type: str = data["type"]
    text_content: str = data.get("content")
    images: Optional[List[FileStorage]] = data.get("images", [])

    if post_type == ContentType.TEXT and not text_content:
        raise InvalidContentType("Text post needs text")

    if post_type == ContentType.PHOTO and not images:
        raise InvalidContentType("Photo post needs images")

    # save images, if any
    for image in images:
        save_image(session, image, post_uuid=post_uuid)

    # save text content, if any
    save_text(session, data, post_uuid=post_uuid)


def save_image(
    session: LocalProxy,
    image: FileStorage,
    post_uuid: Optional[str] = None
) -> None:
    """Save an image.

    This function saves an image to the db regardless of if it is
    as part of a post or not. This is useful for things like
    favicons, which are images but are not a part of a post.

    :param LocalProxy session: db session
    :param FileStorage image: image to save
    :param Optional[str] post_uuid: uuid of post, if image
        is a part of a post.
    """
    path: str = image_proc.save(image)
    uuid: str = utils.get_uuid()
    url_extension: str = secure.generate_unique_token(
        session=session,
        column=models.Images.url_extension,
        func=utils.random_short_string
    )
    session.add(
        models.Images(
            uuid=uuid,
            path=path,
            post_uuid=post_uuid,
            size=os.stat(path).st_size,
            created=get_utc_now(),
            url_extension=url_extension,
        )
    )


def save_text(
    session: LocalProxy,
    data: TextContent,
    post_uuid: Optional[str] = None,
) -> None:
    """Save textual information associated with a post.

    This is an optimistic function from the perspective of the
    caller as it only saves if there is actually anything to save.

    :param LocalProxy session: db session
    :param TextContent data: dict containing text 'stuff'
    :param Optional[str] post_uuid: post id for relationship, if
        text content is a part of a post.
    :param str post_uuid: post id for relationship
    """

    content: bool = data.get("content") or data.get("caption")
    title: Optional[str] = data.get("title")

    if not title and not content:
        return

    session.add(
        models.TextContent(
            post_uuid=post_uuid,
            uuid=utils.get_uuid(),
            title=title,
            content=content,
            created=get_utc_now(),
        )
    )


def get(
    session: LocalProxy,
    domain_name: str
) -> Dict[str, List[PostCollection]]:
    """Get all posts for a given corna.

    :param sqlalchemy.Session session: a db session
    :param str domain_name: the domain name of the corna

    :return: all the posts for a given corna
    :rtype: dict
    :raises NoneExistinCornaError: is the corna does not exist
    """
    corna: models.CornaTable = get_corna(session, domain_name)

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

    parsed_post: TextPost = dict(
        type=post.type,
        created=post.created.isoformat(),
        post_url=post_url,
        content=post.text.content,
    )

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

    parsed_post: ImagePost = dict(
        type=post.type,
        created=post.created.isoformat(),
        post_url=post_url,
        image_urls=url_list
    )

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


def get_image(session: LocalProxy, domain_name: str, url: str) -> str:
    """Get the file path for an image.

    :param sqlalchemy.Session session: a db session
    :param str domain_name: the corna the picture is posted on
    :param str url: the dedicated url extension of the post

    :return: the file path to the image
    :rtype: str
    :raises PostDoesNotExist: if the post does not exist
        or the post is not associated with the corna
    :raises InvalidContentType: if the post type is not an image
    """
    image: Optional[models.Images] = (
        session
        .query(models.Images)
        .filter(models.Images.url_extension == url)
        .one_or_none()
    )
    if image is None:
        raise PostDoesNotExist("Post does not exist")

    post: Optional[models.PostTable] = image.post
    if not post.corna.domain_name == domain_name:
        # not exactly right description, here we are testing
        # if the domain_name matches the corna associated with
        # the post, so technically this is a "post does not exist"
        # error as even if the post is in the db, it is not on
        # the corna we care about.
        raise PostDoesNotExist("Post does not exist")

    if not post.type == ContentType.PHOTO:
        raise InvalidContentType("This is not a image")

    return image.path
