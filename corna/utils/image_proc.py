"""Image processing functionality."""

import hashlib
import logging
import os
import random
from typing import Callable, Optional, Set

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from corna.utils import mkdir

logger = logging.Logger(__name__)

IMAGE_EXTENSIONS: Set[str] = {"gif", "jpg", "jpeg", "png", "webp"}
PICTURE_DIR: Optional[str] = os.environ.get("PICTURE_DIR")
# Using md5 there seems to be some small chance of collisions
# however, my maths is not good enough to calculate it myself
# and there seems to be some conflicting points RE answers I've
# found online.
# For more discussion: https://stackoverflow.com/q/201705
DIGESTMOD: Callable = hashlib.md5
READ_BYTES: int = 8192


def random_hash() -> str:
    """Create random 128 bit 'hash'.

    We want a hash value to be associated with all files. In the future,
    we will implement finger printing for all media files but in the
    meantime we will give hard-to-hash media files (e.g. video) as random
    hash.

    :returns: hex representation of a random 128 bit number
    :rtype: str
    """
    r_hash: int = random.getrandbits(128)
    return hex(r_hash)[2:]


def hash_image(image_path: FileStorage) -> str:
    """Hash an image using the global digest algorithm.

    :param FileStorage image_path: FileStorage object containing image.
    :returns: hexadecimal representation of the hash
    :rtype: str
    """
    digest: object = DIGESTMOD()

    while True:
        # read 8KB chunks
        nxt: bytes = image_path.read(READ_BYTES)
        if not nxt:
            break
        digest.update(nxt)

    # reset read pointer to start of file
    image_path.seek(0)
    return digest.hexdigest()


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


def save(image: FileStorage, bucket: str, hash_: str) -> str:
    """Save an image to disk.

    :param flask.FileStorage image: the image to save
    :param str bucket: the "bucket" (read: type) of the media file
        e.g. thumbnail, avatar, video etc
    :param str hash_: hash value associated with the file
    :returns: the full path of the image
    :rtype: str
    :raises OSError: if image cannot be saved
    """
    if not image.filename:
        raise OSError("File needs name to be saved")

    secure_image_name: str = secure_filename(image.filename)
    hashed_dir: str = hash_to_dir(hash_)
    # combination of the root assets dir and the hash derived fs
    directory_path: str = f"{PICTURE_DIR}/{bucket}/{hashed_dir}"

    # Eventually we will replace this with either a `phash` or `dhash`
    # to check for similarity but this is a useful initial tool to use
    # in monitoring and obvious duplicates
    try:
        mkdir(directory_path, exists_ok=False)

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
        image.save(full_path)
    except OSError as e:
        raise e

    # we do not want to save the full path to the image which includes
    # `PICTURE_DIR` because `PICTURE_DIR` is not guaranteed to always be
    # in the same place. However, the hashed fs will always exits so we can
    # defer the responsibility of finding the correct `PICUTRE_DIR` to the
    # download code.
    return f"{bucket}/{hashed_dir}/{secure_image_name}"


def size(path: str) -> int:
    """Get file size of an image.

    Due to `PICTURE_DIR` potentially moving at any point we
    only want to save the hashed fs in our db. To figure out the
    full path we need to access to `PICTURE_DIR`, so in order to
    simplify this process its best to have this in one place.

    :param str path: the hashed fs path to the file
    :returns: size of file
    :rtype: int
    :raises OSError: if file does not exist
    """
    full_path: str = f"{PICTURE_DIR}/{path}"
    try:
        result: int = os.stat(full_path).st_size

    except OSError as e:
        logger.error(e)
        raise e

    return result


def is_image(filename: str) -> bool:
    """Verify is a file is an image.

    :param str filename: the name of the media file
    :return: true if file is an image
    :rtype: bool
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in IMAGE_EXTENSIONS
    )
