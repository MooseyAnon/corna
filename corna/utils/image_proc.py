"""Image processing functionality."""

from fractions import Fraction
import hashlib
import io
import logging
import os
import pathlib
import random
import tempfile
from typing import Callable, Set

import cv2
import numpy as np
from werkzeug.datastructures import FileStorage

from corna import config, enums
from corna.middleware import storage
from corna.utils import utils

logger = logging.Logger(__name__)

IMAGE_EXTENSIONS: Set[str] = {"gif", "jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS: Set[str] = {"avi", "flv", "mkv", "mp4", "mov", "wmv"}
# 100MB - current file size limit for images/videos
MAX_BLOB_SIZE: int = 100 * 1024 * 1024
# 3MB - The amount of data we send back to the browser for each range
# request on a large file.
#
# This is a tradeoff:
# - Larger chunks keep the streaming connection open for longer, which can
#   provide a more consistent stream, but they also tie up server resources
#   for longer.
# - Smaller chunks give the browser more opportunities to disconnect, freeing
#   server resources sooner, but result in more requests.
#
# The goal is to find the right balance. Larger chunks can also provide a
# worse experience on slower or less reliable internet connections.
RANGE_RESPONSE_SIZE = 3 * 1024 * 1024
# Using md5 there seems to be some small chance of collisions
# however, my maths is not good enough to calculate it myself
# and there seems to be some conflicting points RE answers I've
# found online.
# For more discussion: https://stackoverflow.com/q/201705
DIGESTMOD: Callable = hashlib.md5
READ_BYTES: int = 8192


def get_workdir() -> pathlib.Path:
    """Get the chunkdir/tmp scratch space."""
    # directory for holding media chunks for large files. This dir gets
    # periodically cleaned up.
    return config.get_config().app.upload_tmp_dir


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

    suffix: str = pathlib.Path(image.filename).suffix
    new_file_name: str = utils.random_short_string(16)
    hashed_dir: str = hash_to_dir(hash_)
    # combination of the root assets dir and the hash derived fs
    full_path: str = f"{bucket}/{hashed_dir}/{new_file_name}{suffix}"
    store = storage.get_storage()

    # save picture
    try:
        store.save_file(full_path, image, content_type=image.content_type)
    except OSError as e:
        raise e

    # save file reads the file till the end. Its up to the stream user to be
    # a good citizen and seek back to the start so other upstream blocks of
    # code can read the file without worrying about the pointer position
    image.seek(0)
    return full_path


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
    store = storage.get_storage()
    try:
        result: int = store.size(path)

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


def is_video(filename: str) -> bool:
    """Verify is a file is an video.

    :param str filename: the name of the media file
    :return: true if file is an video
    :rtype: bool
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in VIDEO_EXTENSIONS
    )


# pylint: disable=no-member
def image_dimensions(image: FileStorage) -> tuple[int, int]:
    """Get the image dimensions.

    :param FileStorage image: the image
    :return: a tuple containing the height and width (in that order)
    :rtype: tuple
    :raises FileNotFoundError: if file can't be read
    :raises ValueError: if the file is empty
    """
    np_arr: np.ndarray = np.frombuffer(image.read(), np.uint8)
    img: np.ndarray = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise FileNotFoundError(f"Can't read file with name '{image.name}'")

    height, width, _ = img.shape

    if height == 0:
        raise ValueError("Invalid image: image height is 0.")

    image.seek(0)
    return height, width


# pylint: disable=no-member
def video_dimensions(video: FileStorage) -> tuple[int, int]:
    """Get the dimensions of a video.

    :param FileStorage video: the video
    :return: a tuple containing the height and width (in that order)
    :rtype: tuple
    :raises ValueError: if the file is empty or if file can't be read
    """
    suffix: str = pathlib.Path(video.filename).suffix
    # We need to save to a temp file as openCV can't read from in-mem buffers
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        video.save(tmp)
        tmp_path = tmp.name

    height = width = 0
    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError("Failed to open video file.")

        width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if height == 0:
            raise ValueError(
                "Video height is zero; cannot compute aspect ratio.")

    finally:
        # close connection
        cap.release()
        # Clean up temp file
        os.remove(tmp_path)
        # seek video back to start
        video.seek(0)

    return height, width


def aspect_ratio(height: int, width: int, tolerance=0.02) -> str:
    """Get the aspect ratio of a image or video.

    :param int height: height of image/video
    :param int width: width of image/video
    :param float tolerance: the acceptible error tolerance for lookup misses
        TL;DR this will decided if the "closest" match is too far.
    :returns: aspect ratio in a string format e.e. '16/9'
    :rtype: str
    :raises ValueError: if height is 0 - preventing zero division errors
    """
    # Found this on some random website, I dont even know how legit this is.
    # But covers all the common ratios.
    COMMON_ASPECT_RATIOS: list[tuple[int, int]] = [
        (16, 9),    # Widescreen HD/Full HD/4K
        (4, 3),     # Old TVs, webcams, iPads
        (3, 2),     # Photography (DSLR, 35mm film)
        (1, 1),     # Square (Instagram, profile pics)
        (21, 9),    # Ultra-wide monitors, cinematic
        (18, 9),    # Modern phones (aka 2:1)
        (2, 1),     # Some ultra-wide mobile screens
        (5, 4),     # Old standard monitors (1280x1024)
        (9, 16),    # Portrait video (TikTok, IG Reels)
        (10, 16),   # Instagram stories
        (9, 18),    # Tall phone screens
        (3, 4),     # Portrait webcam
        (2, 3),     # Portrait photography
        (1, 2),     # Very tall images
        (1, 1.91),  # Facebook landscape ads
    ]

    if height == 0:
        raise ValueError("Height cannot be zero")

    actual_ratio: float = width / height

    # find the closest ratio to the actual ratio. This is a minimisation
    # mechanism. The closer (test_ration - actual_ratio) is to 0, the more
    # likely that we've found the correct ratio.
    closest: tuple[int, int] = min(
        COMMON_ASPECT_RATIOS,
        key=lambda r: abs((r[0] / r[1]) - actual_ratio)
    )

    closest_ratio: float = closest[0] / closest[1]
    # the error rate is essentially the difference between the closest ratio
    # and the actual ratio. The closer this is to 0, the better.
    error: float = abs(closest_ratio - actual_ratio) / actual_ratio

    # if the error rate is within our tolerance range, return it
    if error <= tolerance:
        return f"{closest[0]}/{closest[1]}"

    # fallback: return exact simplified ratio
    frac = Fraction(width, height).limit_denominator()
    return f"{frac.numerator}/{frac.denominator}"


def create_thumbnail(media_file: FileStorage, file_type: str) -> FileStorage:
    """Turn a given image into a thumbnail.

    We default to 768x768 but maintain aspect ratio so the largest side
    will be 768px.

    :param FileStorage media_file: the media file
    :param str file_type: the media type of the file e.g. video, image

    :returns: a FileStorage object containing the thumbnail.
    :rtype: FileStorage
    :raise ValueError: if unknown media type is passed in or there was
        an encode/decode error.
    :raises FileNotFoundError: if file reading fails
    """
    match file_type:
        case enums.MediaTypes.VIDEO.value:
            img: np.ndarray = get_video_frame(media_file)
        case (
            enums.MediaTypes.IMAGE.value
            | enums.MediaTypes.AVATAR.value
        ):
            np_arr: np.ndarray = np.frombuffer(media_file.read(), np.uint8)
            img: np.ndarray = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        case _:
            raise ValueError(f"Unknown media type: {file_type}")

    if img is None:
        raise FileNotFoundError(
            f"Can't read file with name '{media_file.filename}'")

    height, width, _ = img.shape
    # we dont want the biggest side being larger than 768px
    max_size: int = 768

    # Ensure we keep the same aspect ratio, e.g.
    #    - 4000×3000 → 768×576
    #    - 3000×4000 → 576×768
    #    - 4000×1000 → 768×192
    #
    # We also ensure that only files larger than 768 x 768 get resized e.g.
    #    - 768 × 576 → 768 × 576
    scale: float = min(1.0, max_size / height, max_size / width)
    new_size: tuple[int, int] = (
        int(width * scale),
        int(height * scale),
    )

    resized_image: np.ndarray = cv2.resize(
        img,
        new_size,
        interpolation=cv2.INTER_AREA,
    )
    # re-encode to JPEG
    success, encoded = cv2.imencode(
        ".jpg",
        resized_image,
        # we dont need perfect quality for thumbnails
        [cv2.IMWRITE_JPEG_QUALITY, 85],
    )

    if not success:
        raise ValueError("Failed to encode thumbnail")

    # store encoded bytes into bytesIO object
    result = io.BytesIO(encoded.tobytes())

    fs_name: str = f"{utils.random_short_string(16)}.jpg"
    thumbnail: FileStorage = utils.to_filestorage(result, fs_name)

    media_file.seek(0)
    return thumbnail


def get_video_frame(video_file: FileStorage) -> np.ndarray:
    """Grab a frame from a video file.

    This defaults to grabbing the first frame.

    :param FileStorage video_file: the video file
    :returns: numpy array containing the first frame of the video
    :rtype: np.ndarray
    :raises ValueError: if video reading fails
    """
    suffix: str = pathlib.Path(video_file.filename).suffix

    # We need to save to a temp file as openCV can't read from in-mem buffers
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        video_file.save(tmp)
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)

    try:
        if not cap.isOpened():
            raise ValueError("Failed to open video file.")

        success, frame = cap.read()

        if not success:
            raise ValueError("Failed to read frame from video")

    finally:
        # close connection
        cap.release()
        # Clean up temp file
        os.remove(tmp_path)
        # seek video back to start
        video_file.seek(0)

    return frame
