"""Manage Corna posts."""

import logging
import os
import random
import string
from typing import Dict, List, Optional, Tuple, Union

from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage
from werkzeug.local import LocalProxy
from werkzeug.utils import secure_filename

from corna.db import models
from corna.enums import ContentType
from corna.utils import get_utc_now, image_proc, secure, utils
from corna.utils.errors import CornaOwnerError
from corna.utils.utils import current_user

logger = logging.Logger(__name__)


PICTURE_DIR: Optional[str] = os.environ.get("PICTURE_DIR")
# to generate "unique-ish" short strings to use for URL extentions
ALPHABET: str = string.ascii_lowercase + string.digits

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


# from: https://stackoverflow.com/q/13484726
def random_short_string(length: int = 8) -> str:
    """Random-ish short string generator.

    :param int length: length of string
    :return: random-ish short string
    :rtype: str
    """
    return "".join(random.choices(ALPHABET, k=length))


def hash_to_dir(hash_32: str) -> str:
    """Construct directory structure from hash.

    This function expects the hexadecimal representation of _at least_ a
    128bit (i.e 16 bytes) hash function output. Typically 128bit to hex
    results in at least 32 hexadecimal digits (2 digits per byte).

    :param str hash_32: the image hash to use for the directory structure.
    :returns: The hash broken down into a directory structure e.g.
        in: b064a10c720babc723728f9ffd58f472
        out: b06/4a1/0c7/20babc723728f9ffd58f472
    rtype: str
    """
    # This directory structure allows us to "balance" pictures more
    # uniformly rather relying on something that does not have great
    # distribution like directories prefixed with user IDs or something.
    # More discussion: https://stackoverflow.com/a/900528
    path: str = f"{hash_32[:3]}/{hash_32[3:6]}/{hash_32[6:9]}/{hash_32[9:]}"
    return path


def handle_pictures(picture: FileStorage) -> str:
    """Handle the saving of a picture.

    :param flask.FileStorage picture: the picture to save
    :returns: the full path of the picture
    :rtype: str
    :raises OSError: if picture cannot be saved
    """
    if not picture.filename:
        raise OSError("File needs name to be saved")

    secure_image_name: str = secure_filename(picture.filename)
    image_hash: str = image_proc.hash_image(picture)
    # combination of the root assets dir and the hash derived fs
    directory_path: str = f"{PICTURE_DIR}/{hash_to_dir(image_hash)}"

    # Eventually we will replace this with either a `phash` or `dhash`
    # to check for similarity but this is a useful initial tool to use
    # in monitoring and obvious duplicates
    try:
        utils.mkdir(directory_path, exists_ok=False)

    except FileExistsError as error_message:
        logger.warning(
            "Photo directory exists, duplicate? Dir path: %s. "
            "Name of image: %s. Error: %s",
            directory_path,
            secure_image_name,
            error_message,
        )

    full_path: str = f"{directory_path}/{secure_image_name}"
    # save picture
    try:
        picture.save(full_path)
    except OSError as e:
        raise e

    return full_path


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
        func=random_short_string
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

    images: Optional[List[FileStorage]] = data.get("images", [])
    for image in images:
        save_image(session, image, post_uuid=post_uuid)

    save_text(session, data, post_uuid=post_uuid)

    logger.info("successfully added new post!")


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
    path: str = handle_pictures(image)
    uuid: str = utils.get_uuid()
    url_extension: str = secure.generate_unique_token(
        session=session,
        column=models.Images.url_extension,
        func=random_short_string
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

    return {"posts": [parse_post(post) for post in posts]}


def parse_post(post: models.PostTable) -> PostCollection:
    """Correctly parse the out going post.

    :param models.PostTable post: a row from the database
    :return: a dict with the required fields
    :rtype: dict
    """
    domain_name: str = post.corna.domain_name
    url: str = build_url(post.url_extension, domain_name, post.type)

    data: PostCollection = dict(
        type=post.type,
        created=post.created.isoformat(),
        post_url=url,
    )

    if post.text.title:
        data["title"] = post.text.title

    if post.text.content:
        key: str = "content" if post.type == "text" else "caption"
        data[key] = post.text.content

    if post.images:
        url_list: List[str] = [
            build_url(image.url_extension, domain_name, "image")
            for image in post.images
        ]
        data["image_urls"] = url_list

    return data


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
