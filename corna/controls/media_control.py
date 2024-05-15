"""Control layer for dealing with media files."""

import logging
from typing import Optional

from sqlalchemy.orm.scoping import scoped_session as Session
from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage

from corna.db import models
from corna.middleware import alchemy
from corna.utils import get_utc_now, image_proc, secure, utils

logger = logging.getLogger(__name__)


class UploadResponse(TypedDict):
    """Response type for uploads."""

    id: str
    filename: str
    mime_type: str
    size: int
    url_extension: str


def _image(
    session: Session,
    hash: str,  # pylint: disable=redefined-builtin
) -> str:
    """Save a new image to the DB.

    :param Session session: connection to the DB
    :param str hash: the hash of the image
    :returns: image UUID
    :rtype: str
    """
    uuid: str = utils.get_uuid()
    session.add(models.Images(uuid=uuid, hash=hash))
    return uuid


def upload(
    session: Session,
    image: FileStorage,
    type: str,  # pylint: disable=redefined-builtin
) -> UploadResponse:
    """Upload an image.

    :param Session session: db session
    :param FileStorage image: The image to save
    :param str type: The type of file being uploaded
    :returns: information about the unloaded image
    :rtype: UploadResponse
    """
    image_uuid: Optional[str] = None
    if image_proc.is_image(image.filename):
        image_hash: str = image_proc.hash_image(image)
        image_uuid = _image(session, image_hash)

    else:
        image_hash: str = image_proc.random_hash()

    url_extension: str = secure.generate_unique_token(
        session=session,
        column=models.Media.url_extension,
        func=utils.random_short_string
    )
    path: str = image_proc.save(image, type, image_hash)
    size: int = image_proc.size(path)
    uuid: str = utils.get_uuid()

    session.add(
        models.Media(
            uuid=uuid,
            path=path,
            size=size,
            type=type,
            orphaned=True,
            post_uuid=None,
            created=get_utc_now(),
            image_uuid=image_uuid,
            url_extension=url_extension,
        )
    )

    response: UploadResponse = {
        "id": uuid,
        "filename": image.filename,
        "mime_type": image.content_type,
        "size": size,
        "url_extension": url_extension,
    }

    return response


def download(session: Session, slug: str) -> str:
    """Download an image.

    :param Session session: db session
    :param str slug: the url extension of the image to download

    :returns: The path to the image
    :rtype: str
    :raises FileNotFoundError: if no image associated with the url exits
    """
    try:
        image: models.Media = alchemy.media_from_slug(session, slug)

    except alchemy.NoMediaError as e:
        raise FileNotFoundError("File not found") from e

    return f"{image_proc.PICTURE_DIR}/{image.path}"
