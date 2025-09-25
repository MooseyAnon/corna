"""Control layer for dealing with media files."""

import logging
import mimetypes
import pathlib
import random
import re
from typing import Iterator, List, Optional

from sqlalchemy.orm.scoping import scoped_session as Session
from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage

from corna.db import models
from corna.enums import MediaTypes
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


class Avatar(TypedDict):
    """Avatar object."""

    url: str
    slug: str


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
        # the werkzeug documentation acknowledges that this is an unreliable
        # way to find the mimetype of a file and more often than not will not
        # be present. In light of this, in the future we need a more robust
        # solution. Look here for more deets: https://stackoverflow.com/q/43580
        "mime_type": mimetypes.guess_type(image.filename, strict=False)[0],
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

    return image


def to_path(media_object: models.Media) -> str:
    """Return the full path of a media object.

    This is relvent as we have different downloading strategies for different
    types of files and we also have to consider the face that the 'picture'
    directory can move (i.e. it could be a directory path or a url path).

    We can also do our existance checks here :)

    :param models.Media media_object: a row from the media table.
    :returns: the full path the the media object
    :rtype: str
    """
    full_path = pathlib.Path(f"{image_proc.PICTURE_DIR}/{media_object.path}")

    if not full_path.exists():
        raise FileNotFoundError("No image found")

    return str(full_path)


def get_range(headers: dict, size: int) -> tuple[int, int] | None:
    """Get the range to be returned for a video file.

    :param dict headers: the request headers
    :param int size: the size of the media file, this is used as a fallback
        for the end of the read-region
    :returns: start and end of the range, if range, else None
    :rtype: tuple[int, int] | None
    """
    range_header: str = headers.get('Range', None)

    if (
        not range_header or
        not (range_match := re.match(r"bytes=(\d+)-(\d*)", range_header))
    ):
        logger.warning("Did not find Range header on video file.")
        return None

    start: int = int(range_match.group(1))
    # end does not always have to be defined
    end_str: Optional[str] = range_match.group(2)
    end: int = int(end_str) if end_str else size - 1

    return start, end


def video_stream(
    path: str,
    start: int,
    end: int,
    read_bytes: int = image_proc.READ_BYTES,
) -> Iterator[bytes]:
    """Generate a video stream.

    :param str path: path to video
    :param int start: byte to start read from
    :param int end: last byte to read
    :param int read_bytes: the number of bytes to read
    :yields: block of data
    :ytype: bytes
    """
    with open(path, "rb") as fd:
        fd.seek(start)

        chunk_length: int = end - start + 1

        while chunk_length > 0:
            read_size: int = min(chunk_length, read_bytes)
            data: bytes = fd.read(read_size)

            if not data:
                break

            yield data
            chunk_length -= len(data)


def random_avatar(session: Session) -> Avatar:
    """Get a random avatar."""

    # Doing this directly in the DB can have performance impacts, especially
    # as the table in question grows larger. As there are relatively few
    # avatars compared to the rest of media files, we can do the random search
    # in python land rather than in the database.
    # more info here:
    #   - https://www.depesz.com/2007/09/16/my-thoughts-on-getting-random-row/
    avatars: List[models.Media] = (
        session
        .query(models.Media)
        .filter(models.Media.type == MediaTypes.AVATAR.value)
        .all()
    )
    avatar: models.Media = random.choice(avatars)

    url: str = \
        f"{utils.UNVERSIONED_API_URL}/v1/media/download/{avatar.url_extension}"

    return {"url": url, "slug": avatar.url_extension}
