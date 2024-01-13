"""Control layer for dealing with media files."""

import logging
import os
from typing import Optional

from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage
from werkzeug.local import LocalProxy

from corna.db import models
from corna.utils import get_utc_now, image_proc, secure, utils

logger = logging.getLogger(__name__)


class UploadResponse(TypedDict):
    """Response type for uploads."""

    id: str
    filename: str
    mime_type: str
    size: int
    url_extension: str


def upload(session: LocalProxy, image: FileStorage) -> UploadResponse:
    """Upload an image.

    :param LocalProxy session: db session
    :param FileStorage image: The image to save
    :returns: information about the unloaded image
    :rtype: UploadResponse
    """
    url_extension: str = secure.generate_unique_token(
        session=session,
        column=models.Images.url_extension,
        func=utils.random_short_string
    )
    path: str = image_proc.save(image)
    size: int = os.stat(path).st_size
    uuid: str = utils.get_uuid()

    session.add(
        models.Images(
            uuid=uuid,
            path=path,
            post_uuid=None,
            size=size,
            created=get_utc_now(),
            url_extension=url_extension,
            orphaned=True,
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


def download(session: LocalProxy, url_extension: str) -> str:
    """Download an image.

    :param LocalProxy session: db session
    :param str url_extension: the url extension of the image to download

    :returns: The path to the image
    :rtype: str
    :raises FileNotFoundError: if no image associated with the url exits
    """
    image: Optional[models.Images] = (
        session
        .query(models.Images)
        .filter(models.Images.url_extension == url_extension)
        .one_or_none()
    )

    if image is None:
        raise FileNotFoundError("File not found")

    return image.path
