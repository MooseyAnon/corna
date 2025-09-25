"""Control layer for dealing with media files."""

import errno
import io
import json
import logging
import mimetypes
import os
import pathlib
import random
import re
import shutil
from typing import Iterator, List, Optional

from sqlalchemy.orm.scoping import scoped_session as Session
from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage

from corna.db import models
from corna.enums import MediaTypes
from corna.middleware import alchemy
from corna.utils import get_utc_now, image_proc, mkdir, secure, utils

logger = logging.getLogger(__name__)


class MergingError(ValueError):
    """Raised if a request tries to initialise merging after it has started."""


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


def process_chunk(
    chunk: FileStorage,
    chunk_index: int,
    total_chunks: int,
    upload_id: str,
) -> dict[str, str | int]:
    """Process an incoming chunk of media blob.

    Using a set atomic read/writes to handle processing incoming chunks of
    media files this function either a) saves the incoming chunk or b) saves
    the entire file to the DB (and blob storage) if upload of chunks is
    complete.

    Each upload comes with a unique upload ID. This serves two functions:
    a) allows us to partition the incoming chunks by upload ID in the local FS
    preventing chunks of different media from being mixed up, b) allows us to
    resume chunking uploads if the client loses connection or needs to retry.

    TODO: handle duplicate chunks. We can check the metadata file for existing
    chunks.

    :param FileStorage chunk: the incoming chunk
    :param int chunk_index: the chunk number relative to the file i.e
        kth chunk in total_size/chunk_size.
    :param int total_chunks: the total number of chunks expected for the file
        i.e. total_size/chunk_size
    :param str upload_id: unique ID for the upload. Used for local FS
        partitioning

    :return: a results object containing upload data of the chunk
    :rtype: dict
    """
    # save chunk
    save_chunk(blob=chunk, upload_id=upload_id, chunk_index=chunk_index)
    # update meta
    saved_chunks: int = update_meta(
        upload_id=upload_id,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
    )

    complete = saved_chunks >= total_chunks

    return {
        "message":
            "upload complete" if complete else f"chunk {chunk_index} stored",
        "received": saved_chunks,
        "total": total_chunks,
        "uploadId": upload_id,
    }


def save_chunk(
    blob: FileStorage,
    upload_id: str,
    chunk_index: int,
):
    """Atomically save a single chunk of a media file to the local FS.

    :param FileStorage blob: the media blob to save
    :param str upload_id: the unique ID associated with the chunk
    :param int chunk_index: the chunk number relative to the file i.e
        kth chunk in total_size/chunk_size.
    """
    # we want all chunks from the same video to be co-located, so we partition
    # based on upload_id. This also makes cleaning up easier as we can delete
    # the partition once the upload is complete without the risk of deleting
    # unrelated chunks.
    #
    # path-to-parts = <file-system>/<chunk-dir>/<upload-id>/parts
    parts_dir: pathlib.Path = mkdir(
        f"{image_proc.CHUNK_DIR}/{upload_id}/parts")

    # save the chunk to a deterministic location: 000000.part, 000001.part, ...
    # with the filename of each part being based on its index
    part_path: pathlib.Path = parts_dir / f"{chunk_index:06d}.part"
    utils.atomic_stream_write(blob, part_path, suffix=".part.tmp")

    # we want to return the base directory for this chunk i.e. the partition
    # so other functions can use it to add other components
    return parts_dir.parent


def merge_chunks(filename: str, upload_id: str) -> FileStorage:
    """Merged chunks of a large file.

    :param str filename: the name of the file
    :param str upload_id: Id associated with the upload

    :returns: werkzeug FileStorage object ready to be saved by backend
    :rtype: FileStorage
    :raises MergingError: if upload not found or is incomplete
    """
    base_dir: pathlib.Path = pathlib.Path(f"{image_proc.CHUNK_DIR}/{upload_id}")

    # check if this is a valid upload
    if not (metadata := utils.load_json(base_dir / "meta.json")):
        raise MergingError(f"No upload associcated with Id '{upload_id}'")

    # check if we've saved all the chunks
    if (missing := metadata["totalChunks"] - len(metadata["received"])) > 0:
        raise MergingError(f"Incomplete file, {missing} chunks missing")

    logger.info("Merging chunks for video with Id: '%s'", upload_id)
    bytestream: io.BytesIO = assembler(
        base_dir=base_dir, total_chunks=metadata["totalChunks"])
    filestorage: FileStorage = utils.to_filestorage(bytestream, filename)
    return filestorage


def assembler(
    base_dir: pathlib.Path,
    total_chunks: int,
) -> io.BytesIO:
    """Atomically assemble chunks of a media file.

    This is a pretty shoddy implementation of 'locking'. This function
    creates a lock file before chunks get merged, if any process tries to start
    a merge operation while the file exists, an error is raised. This is a
    simple way to avoid duplication.

    :param pathlib.Path base_dir: the directory containing the parts of the
        media file. As chunks are partitioned by uploadId, the base_dir is
        essentially the partition the file lives in.
    :param int total_chunks: the expected number of chunks for the file.
        This is sent from the client and is usually calculated as
        chunk_size/file_size

    :returns: the complete media file, as an in memory byte stream via BytesIO
    :rtype: BytesIO
    :raises OSError: if the file size exceed the system max file size
    :raises MergingError: if a process attempts to acquire a lock during
        merging (FileExistsError)
    :raises MergingError: if there is an error during merging (OSError)
    """
    lock: pathlib.Path = base_dir / ".merge.lock"
    parts_dir: pathlib.Path = base_dir / "parts"

    # we dont want to save files that exceed the system limit
    size: int = file_size(parts_dir, total_chunks)
    if size > image_proc.MAX_BLOB_SIZE:
        logger.error(
            "File to large to save. uploadID: '%s', size: '%s'",
            base_dir.stem, size)
        raise OSError(errno.EFBIG, "File too large for processing")

    try:
        # Create a tmp file which acts like a lock. Creating this file is
        # eqivellent to 'acquiring' a lock.
        # Flags:
        #   - os.O_CREAT: Create the file if it doesn't exist.
        #   - os.O_EXCL: Fail if the file already exists
        #   - os.O_WRONLY: Open for write only
        fd: int = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        # concatenate the chunks
        # We write the concatenated file to memory for two reasons:
        # - max size is (currently) 100mb which should be fine in memory
        # - if we write it to a file first, we have to read it back out in
        #   order to turn it into a FileStorage object which is what the
        #   rest of our system expect.
        # TL:DR its faster to read/write the output once, rather than doing two
        # reads on the same file just to write it once.
        bytestream: io.BytesIO = concat_chunks(parts_dir, total_chunks)

    except FileExistsError as e:
        raise MergingError("Merge in progress") from e

    except OSError as e:
        raise MergingError(f"Unable to merge: {str(e)}") from e

    finally:
        # cleanup lock if it was successfully acquired
        if lock.exists():
            os.unlink(str(lock))

    return bytestream


def update_meta(
    upload_id: str,
    chunk_index: int,
    total_chunks: int,
) -> int:
    """Update meta data file for upload.

    Each file upload has its own meta data file which lives in its partition.

    :param str upload_id: the unique ID associated with the chunk
    :param int chunk_index: The chunks are uploaded as a continous stream,
        this is the number (or index) of the chunk being saved relative to
        the total number of chunks for the file i.e if this is the Kth chunk
        of the file, then chunk_index == K.
    :param int total_chunks: the expected number of chunks for the file.
        This is sent from the client and is usually calculated as
        chunk_size/file_size

    :returns: the number of successfully received chunks
    :rtype: int
    """
    meta_path: str = f"{image_proc.CHUNK_DIR}/{upload_id}/meta.json"
    # default empty dict to use if there is not pre-existing metadata file
    meta: dict[str, str | int] = {}

    if (metadata := utils.load_json(meta_path)):
        # use pre-existing data
        meta.update(metadata)

    # Track received indexes (dedupe)
    rec: set[int] = set(meta.get("received", []))
    rec.add(chunk_index)
    meta["received"] = sorted(rec)
    meta["totalChunks"] = total_chunks

    utils.atomic_text_write(pathlib.Path(meta_path), json.dumps(meta))

    return len(rec)


def concat_chunks(
    parts_dir: pathlib.Path,
    total_chunks: int,
) -> io.BytesIO:
    """Concatenate chunks of a media file.

    This function ignores any duplicates by taking advantage of the index based
    naming convention of the chunks.

    Furthermore, we write the concatenated file to memory.
    This is for two reasons:
      - max size is (currently) 100mb which should be fine in memory
      - if we write it to a file first, we have to read it back out in
        order to turn it into a FileStorage object which is what the
        rest of our system expect.
    TL:DR its faster to read/write the output once, rather than doing two
    reads on the same file just to write it once.

    :param pathlib.Path parts_dir: the directory containing the parts
    :param int total_chunks: the total number of chunks expected
    :return: the merged file in memory as a bytesteam
    :rtype: io.BytesIO
    """
    stream = io.BytesIO()
    # Merge in deterministic order: 000000.part, 000001.part, ...
    # with open(final_path, "wb") as out:
    for i in range(total_chunks):
        part: pathlib.Path = parts_dir / f"{i:06d}.part"
        with open(part, "rb") as src:
            # 1MB copy buffer
            shutil.copyfileobj(src, stream, length=1024 * 1024)

    # reset stream
    stream.seek(0)
    return stream


def clean_chunks(upload_id: str) -> None:
    """Clean up chunk artifacts.

    :param str upload_id: the upload_id associated with the media file
        being uploaded.
    """
    # base_dir for a partition is: <FS>/<chunks-dir>/<uploadID>
    base_dir = pathlib.Path(f"{image_proc.CHUNK_DIR}/{upload_id}")
    meta_path: pathlib.Path = base_dir / "meta.json"
    chunk_dir: pathlib.Path = base_dir / "parts"

    logger.info("deleting artifacts of upload '%s'...", upload_id)

    for chunk in chunk_dir.iterdir():
        chunk.unlink(missing_ok=True)

    chunk_dir.rmdir()
    meta_path.unlink(missing_ok=True)
    base_dir.rmdir()

    logger.info("successfully deleted artifacts for upload '%s'", upload_id)


def file_size(parts_dir: pathlib.Path, total_chunks: int) -> int:
    """Calculate the file size based on chunks.

    While we could do: chunk[0] * total_chunks, to calculate the file size
    it is not guarenteed that the caller (and clients) will upload at a
    consistent rate. We have a size limit on nginx but it relatively high
    and offers a lot of room for variation in upload size of chunks.

    The safest approach is the stupidest one: loop through and count.

    This function takes advantage of the index based naming convention of the
    chunk and thus can avoid any duplicated or malformed chunks.

    :param pathlib.Path parts_dir: the directory containing the chunks
    :param int total_chunks:
    :return: the total size of the file
    :rtype: int
    """
    total_size: int = 0
    for i in range(total_chunks):
        path: pathlib.Path = parts_dir / f"{i:06d}.part"
        total_size += os.stat(path).st_size
    return total_size
