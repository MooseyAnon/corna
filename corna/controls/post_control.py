"""Manage Corna posts."""
import datetime
import logging
import os
import random
import string
from typing import Any, Callable, Dict, List, Optional

from werkzeug.utils import secure_filename

from corna.db import models
from corna.enums import ContentType
from corna.utils import image_proc, secure, utils
from corna.utils.errors import (
    CornaOwnerError, NotLoggedInError, NoneExistingUserError)


logger = logging.Logger(__name__)


PICTURE_DIR: str = os.environ.get("PICTURE_DIR")
# to generate "unique-ish" short strings to use for URL extentions
ALPHABET: List[str] = string.ascii_lowercase + string.digits


class NoneExistinCornaError(ValueError):
    """Blog does not exists."""


class InvalidContentType(ValueError):
    """Content type is not valid."""


class PostDoesNotExist(ValueError):
    """Post does not exit."""


# from: https://stackoverflow.com/questions/13484726/safe-enough-8-character-short-unique-random-string
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


def handle_pictures(picture: Any) -> str:
    """Handle the saving of a picture.

    :param flask.FileStorage picture: the picture to save
    :returns: the full path of the picture
    :rtype: str
    """
    secure_image_name: str = secure_filename(picture.filename)
    image_hash: str = image_proc.hash_image(secure_image_name)
    # combination of the root assets dir and the hash derived fs
    directory_path: str = f"{PICTURE_DIR}/{hash_to_dir(image_hash)}"

    # Eventually we will replace this with either a `phash` or `dhash`
    # to check for similarity but this is a useful initial tool to use
    # in monitoring and obvious duplicates
    try:
        utils.mkdir(directory_path, exists_ok=False)

    except FileExistsError as e:
        logger.warning(
            f"Photo directory exists, duplicate? Dir path: {directory_path}. "
            f"Name of image: {secure_image_name}"
        )

    full_path: str = f"{directory_path}/{secure_image_name}"
    # save picture
    try:
        picture.save(full_path)
    except OSError as e:
        raise e

    return full_path


def text_post(session: Any, data: Dict[str, Any]) -> str:
    """Save a new text post.

    :param sqlalchemy.Session session: a db session
    :param dict data: data to save

    :return: uuid of the post (as string)
    :rtype: str
    """
    uuid: str = utils.get_uuid()
    session.add(
        models.TextPost(
            uuid=uuid,
            title=data["title"],
            body=data["content"],
        )
    )
    return uuid


def photo_post(session: Any, data: Dict[str, Any]) -> str:
    """Save a new photo post.

    :param sqlalchemy.Session session: a db session
    :param dict data: data to save

    :return: uuid of the post (as string)
    :rtype: str
    """
    url_extension: str = secure.generate_unique_token(
        session, models.PhotoPost.url_extension, func=random_short_string)
    path: str = handle_pictures(data["picture"])
    uuid: str = utils.get_uuid()

    session.add(
        models.PhotoPost(
            uuid=uuid,
            url_extension=url_extension,
            path=path,
            caption=data["caption"],
            size=os.stat(path).st_size,
        )
    )
    return uuid


def post_mapper(
    session: Any,
    post_uuid: str,
    obj_uuid: str,
    new_post_type: str,
) -> None:
    """Create mapper object.

    This table in the database maps post metadata to
    post type tables (e.g. text post table or photo post table)
    which contain more specific data to each type of post.

    While this design has some overhead it goes a long way to
    normalising the database and making it easier to reason about
    and extend.

    :param sqlalchemy.Session session: a db session.
    :param str post_uuid: uuid pointing to the post metadata
    :param str obj_uuid: the uuid of the actual object type to be
        saved
    :param str new_post_type: the string representing the type of
        post the incoming post is. This is to ensure foreign relationships
        are created properly.
    :raises InvalidContentType: for unexpected post types
    """
    mapper: object = models.PostObjectMap(
        uuid=utils.get_uuid(),
        post_uuid=post_uuid,
    )
    # we need to make sure this is mutually exclusive
    if new_post_type == ContentType.TEXT:
        mapper.text_post_uuid = obj_uuid

    elif new_post_type == ContentType.PHOTO:
        mapper.photo_post_uuid = obj_uuid

    else:
        raise InvalidContentType(f"Invalid content type: {new_post_type}")

    session.add(mapper)


def post_factory(post_type: str) -> Callable:
    """Returns the correct model builder function for the post type.

    :param str post_type: the type of incoming post
    :return: a callable function signature for the post type
    :rtype: Callable
    :raises InvalidContentType: for unexpected post types
    """
    if post_type == ContentType.TEXT:
        return text_post

    if post_type == ContentType.PHOTO:
        return photo_post

    else:
        raise InvalidContentType(f"Invalid content type: {post_type}")


def create(session: Any, data: Dict[Any, Any]) -> None:
    """Create a new corna post.

    :param sqlalchemy.Session session: a db session
    :param dict data: the incoming data to be saved
    :raises NoneExistinCornaError: if corna does not exist
    :raises NotLoggedInError: user not logged in
    :raises CornaOwnerError: user does not own the corna
    """
    blog: Optional[object] = (
        session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == data["domain_name"])
        .one_or_none()
    )

    if blog is None:
        raise NoneExistinCornaError("corna does not exist")

    # cookies are signed, they need to be unsigned and decoded
    cookie: str = secure.decoded_message(data["cookie"])
    user_session: Optional[object] = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie)
        .one_or_none()
    )

    if user_session is None:
        raise NotLoggedInError("User not logged in")

    if not user_session.user_uuid == blog.user_uuid:
        raise CornaOwnerError("Current user does not own the blog")

    object_uuid: str = post_factory(data["type"])(session, data)
    post_uuid: str = utils.get_uuid()

    session.add(
        models.PostTable(
            post_uuid=post_uuid,
            blog_uuid=blog.blog_uuid,
            created=utils.get_utc_now(),
            deleted=False,
            type=data["type"],
        )
    )
    post_mapper(session, post_uuid, object_uuid, data["type"])
    logger.info("successfully added new post!")


def get(session: Any, domain_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get all posts for a given corna.

    :param sqlalchemy.Session session: a db session
    :param str domain_name: the domain name of the corna

    :return: all the posts for a given corna
    :rtype: dict
    :raises NoneExistinCornaError: is the corna does not exist
    """
    corna: Optional[object] = (
         session
        .query(models.CornaTable)
        .filter(models.CornaTable.domain_name == domain_name)
        .one_or_none()
    )

    if corna is None:
        raise NoneExistinCornaError("corna does not exist")

    posts: Optional[object] = (
        session.
        query(models.PostTable)
        .filter(models.PostTable.blog_uuid == corna.blog_uuid)
    )

    return {"posts": [parse_post(post) for post in posts]}


def parse_post(post: object) -> Dict[str, Any]:
    """Correctly parse the out going post.

    :param object post: a row from the database
    :return: a dict with the required fields
    :rtype: dict
    """
    if post.type == "text":
        p: object = post.mapper.text
        data: Dict[str, Any] = dict(
            type=post.type,
            created=post.created.isoformat(),
            title=p.title,
            body=p.body,
        )

    elif post.type == "picture":
        p: object = post.mapper.photo
        data: Dict[str, Any] = dict(
            type=post.type,
            created=post.created.isoformat(),
            url=p.url_extension,
            caption=p.caption,
        )

    return data


def get_image(session: Any, domain_name: str, url: str) -> str:
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
    image = (
        session
        .query(models.PhotoPost)
        .filter(models.PhotoPost.url_extension == url)
        .one_or_none()
    )
    if image is None:
        raise PostDoesNotExist("Post does not exist")

    post = image.mapper.post
    if not post.blog.domain_name == domain_name:
        # not exactly right description, here we are testing
        # if the domain_name matches the corna associated with
        # the post, so technically this is a "post does not exist"
        # error as even if the post is in the db, it is not on
        # the corna we care about.
        raise PostDoesNotExist("Post does not exist")

    if not post.type == ContentType.PHOTO:
        raise InvalidContentType("This is not a image")

    return image.path
