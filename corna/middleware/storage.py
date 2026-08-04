"""Persistent media storage abstraction."""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from functools import lru_cache
import os
from pathlib import Path
import shutil
import tempfile
from typing import BinaryIO, Iterator, Protocol, runtime_checkable

from corna.config import get_config

DEFAULT_READ_SIZE = 8192


class StorageError(Exception):
    """Base exception for persistent media storage errors.

    All storage-specific exceptions inherit from this type so callers can
    handle media storage failures consistently.
    """


class InvalidStorageKeyError(StorageError, ValueError):
    """Raised when a storage key is invalid or unsafe.

    Keys are rejected when they are empty, absolute, contain null bytes, or
    could escape the configured backend root.
    """


class StorageObjectNotFoundError(StorageError, FileNotFoundError):
    """Raised when an object does not exist in persistent storage."""


class StorageObjectExistsError(StorageError, FileExistsError):
    """Raised when an object exists and overwriting is disabled."""


class StorageReadError(StorageError):
    """Raised when an object cannot be read."""


class StorageWriteError(StorageError):
    """Raised when an object cannot be written."""


class StorageDeleteError(StorageError):
    """Raised when an object cannot be deleted."""


@runtime_checkable
class StorageBackend(Protocol):
    """Backend contract for persistent media storage.

    Backends are responsible for translating logical storage keys into their
    underlying representation, such as local filesystem paths or S3 keys.

    Backends must not expose implementation-specific paths, URLs, clients, or
    response objects to callers.

    :ivar save_file: Persist an object stream under a logical key.
    :ivar open_stream: Open an object as a managed readable stream.
    :ivar size: Return object size metadata.
    :ivar delete: Delete an object from persistent storage.
    """

    def save_file(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str | None = None,
        overwrite: bool = False,
    ) -> None:
        """Persist the complete contents of a readable binary stream.

        The stream is read from its current position. The caller remains
        responsible for closing the supplied stream.

        On success, readers must not observe a partially written object.

        :param key: Backend-independent logical storage key.
        :param stream: Binary stream containing the object data.
        :param content_type: Optional MIME type associated with the object.
        :param overwrite: Whether an existing object may be replaced.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageObjectExistsError: If the key exists and overwrite is
            disabled.
        :raises StorageWriteError: If the object cannot be persisted.
        """

    def open_stream(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> AbstractContextManager[BinaryIO]:
        """Open an object as a readable binary stream.

        The returned context manager owns the underlying resource and must
        close it when the context exits.

        When a range is provided, both boundaries are inclusive.

        :param key: Backend-independent logical storage key.
        :param start: Optional first byte to expose.
        :param end: Optional final byte to expose, inclusive.
        :returns: Context manager yielding a readable binary stream.
        :raises InvalidStorageKeyError: If the key or range is invalid.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If the object cannot be opened.
        """

    def size(self, key: str) -> int:
        """Return the object's size in bytes.

        :param key: Backend-independent logical storage key.
        :returns: Object size in bytes.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If its metadata cannot be read.
        """

    def delete(self, key: str) -> None:
        """Delete an object.

        Deletion is idempotent. Deleting a missing object should succeed.

        :param key: Backend-independent logical storage key.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageDeleteError: If deletion fails.
        """


class Storage:
    """Application-facing persistent media storage façade.

    Callers depend on this class rather than concrete local or S3 backends.
    Backend selection and construction happen once during application
    initialisation.

    :param backend: Concrete backend implementing the storage contract.
    """

    def __init__(self, backend: StorageBackend) -> None:
        """Create application-facing storage around a backend.

        :param backend: Concrete persistent storage backend.
        """
        self._backend = backend

    def save_file(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str | None = None,
        overwrite: bool = False,
    ) -> None:
        """Persist an object using its logical storage key.

        :param key: Backend-independent logical storage key.
        :param stream: Binary stream containing the object data.
        :param content_type: Optional MIME type associated with the object.
        :param overwrite: Whether an existing object may be replaced.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageObjectExistsError: If the key exists and overwrite is
            disabled.
        :raises StorageWriteError: If the object cannot be persisted.
        """
        self._validate_key(key)
        try:
            # ensure we reset the stream to the start so we dont save partial
            # or empty files
            stream.seek(0)
        except (AttributeError, OSError):
            # Some readable streams are not seekable. In that case, copy
            # from the stream's current position.
            pass

        self._backend.save_file(
            key,
            stream,
            content_type=content_type,
            overwrite=overwrite,
        )

    def open_stream(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> AbstractContextManager[BinaryIO]:
        """Open an object as a managed readable stream.

        :param key: Backend-independent logical storage key.
        :param start: Optional first byte to expose.
        :param end: Optional final byte to expose, inclusive.
        :returns: Context manager yielding a readable binary stream.
        :raises InvalidStorageKeyError: If the key or range is invalid.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If the object cannot be opened.
        """
        self._validate_key(key)
        self._validate_range(start=start, end=end)

        return self._backend.open_stream(
            key,
            start=start,
            end=end,
        )

    def iter_bytes(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
        chunk_size: int = DEFAULT_READ_SIZE,
    ) -> Iterator[bytes]:
        """Yield an object's contents in bounded chunks.

        This method owns and closes the backend stream. It is suitable for
        application-proxied HTTP responses and range-based video streaming.

        The end boundary is inclusive.

        :param key: Backend-independent logical storage key.
        :param start: Optional first byte to yield.
        :param end: Optional final byte to yield, inclusive.
        :param chunk_size: Maximum bytes to yield per chunk.
        :returns: Iterator yielding object bytes.
        :raises ValueError: If ``chunk_size`` is not positive.
        :raises InvalidStorageKeyError: If the key or range is invalid.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If the object cannot be read.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        self._validate_key(key)
        self._validate_range(start=start, end=end)

        remaining = (
            end - start + 1
            if start is not None and end is not None
            else None
        )

        with self._backend.open_stream(
            key,
            start=start,
            end=end,
        ) as stream:
            while remaining is None or remaining > 0:
                read_size = (
                    chunk_size
                    if remaining is None
                    else min(chunk_size, remaining)
                )

                data = stream.read(read_size)

                if not data:
                    break

                yield data

                if remaining is not None:
                    remaining -= len(data)

    def size(self, key: str) -> int:
        """Return an object's size in bytes.

        :param key: Backend-independent logical storage key.
        :returns: Object size in bytes.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If its metadata cannot be read.
        """
        self._validate_key(key)
        return self._backend.size(key)

    def delete(self, key: str) -> None:
        """Delete an object from persistent storage.

        :param key: Backend-independent logical storage key.
        :raises InvalidStorageKeyError: If the key is invalid.
        :raises StorageDeleteError: If deletion fails.
        """
        self._validate_key(key)
        self._backend.delete(key)

    @staticmethod
    def _validate_key(key: str) -> None:
        """Perform backend-independent logical-key validation.

        :param key: Logical storage key to validate.
        :raises InvalidStorageKeyError: If the key is empty, absolute,
            contains null bytes, or contains unsafe path segments.
        """
        if not key:
            raise InvalidStorageKeyError(
                "Storage key must not be empty"
            )

        if "\x00" in key:
            raise InvalidStorageKeyError(
                "Storage key must not contain null bytes"
            )

        if key.startswith(("/", "\\")):
            raise InvalidStorageKeyError(
                "Storage key must be relative"
            )

        parts = key.replace("\\", "/").split("/")

        if any(part in {"", ".", ".."} for part in parts):
            raise InvalidStorageKeyError(
                f"Invalid storage key: {key!r}"
            )

    @staticmethod
    def _validate_range(
        *,
        start: int | None,
        end: int | None,
    ) -> None:
        """Validate an optional inclusive byte range.

        :param start: Optional first byte in the range.
        :param end: Optional final byte in the range, inclusive.
        :raises InvalidStorageKeyError: If the range is negative,
            incomplete, or ordered incorrectly.
        """
        if start is not None and start < 0:
            raise InvalidStorageKeyError(
                "Range start must not be negative"
            )

        if end is not None and end < 0:
            raise InvalidStorageKeyError(
                "Range end must not be negative"
            )

        if start is None and end is not None:
            raise InvalidStorageKeyError(
                "Range end cannot be provided without range start"
            )

        if (
            start is not None
            and end is not None
            and end < start
        ):
            raise InvalidStorageKeyError(
                "Range end must be greater than or equal to range start"
            )


class LocalStorageBackend:
    """Persistent media storage backed by the local filesystem.

    :param root: Root directory beneath which all storage objects are kept.
    """

    def __init__(self, root: str | Path) -> None:
        """Create a local filesystem storage backend.

        :param root: Root directory beneath which all storage objects are kept.
        """
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str | None = None,
        overwrite: bool = False,
    ) -> None:
        """Atomically persist a stream beneath the configured root.

        ``content_type`` is accepted to satisfy the common backend interface,
        but local filesystem storage does not currently persist MIME metadata.

        :param key: Backend-independent logical storage key.
        :param stream: Binary stream containing the object data.
        :param content_type: Optional MIME type, currently ignored locally.
        :param overwrite: Whether an existing object may be replaced.
        :raises StorageObjectExistsError: If the key exists and overwrite is
            disabled.
        :raises StorageWriteError: If the object cannot be persisted.
        """
        del content_type

        destination = self._resolve_key(key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not overwrite and destination.exists():
            raise StorageObjectExistsError(
                f"Storage object already exists: {key!r}"
            )

        temporary_path: Path | None = None

        try:

            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(file_descriptor, "wb") as destination_stream:
                shutil.copyfileobj(
                    stream,
                    destination_stream,
                    length=1024 * 1024,
                )

                destination_stream.flush()
                os.fsync(destination_stream.fileno())

            if overwrite:
                temporary_path.replace(destination)
            else:
                self._publish_without_overwrite(
                    temporary_path,
                    destination,
                    key,
                )

            temporary_path = None

        except StorageObjectExistsError:
            # this is temp. The chances of duplication are slim, for this
            # to happen, the following needs to be true:
            # - re-upload of the same pieces of media in the same aspect ratio
            # and quality (entirely possible with popular media)
            # - it must have the same file name (less likely)
            #
            # However, we will be fixing this regardless by renaming all
            # incoming files. We may keep the original filename for display
            # purposes.
            raise

        except OSError as error:
            raise StorageWriteError(
                f"Unable to save storage object: {key!r}"
            ) from error

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @contextmanager
    def open_stream(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,  # pylint: disable=unused-argument
    ) -> Iterator[BinaryIO]:
        """Open a local object as a managed binary stream.

        The stream is positioned at ``start`` when supplied. The caller or
        façade remains responsible for limiting reads to ``end``.

        :param key: Backend-independent logical storage key.
        :param start: Optional first byte to expose.
        :param end: Optional final byte to expose, inclusive.
        :returns: Iterator yielding a readable binary stream.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If the object cannot be opened or read.
        """
        path = self._resolve_key(key)

        try:
            stream = path.open("rb")
        except FileNotFoundError as error:
            raise StorageObjectNotFoundError(
                f"Storage object not found: {key!r}"
            ) from error
        except OSError as error:
            raise StorageReadError(
                f"Unable to open storage object: {key!r}"
            ) from error

        try:
            # `end` is intentionally ignored. The Storage façade limits the
            # total bytes read, while the backend only needs to position the
            # stream at the requested starting offset.
            #
            # `end` is needed to maintain consistency with other backends which
            # do require it.
            if start is not None:
                stream.seek(start)

            yield stream

        except OSError as error:
            raise StorageReadError(
                f"Unable to read storage object: {key!r}"
            ) from error

        finally:
            stream.close()

    def size(self, key: str) -> int:
        """Return the size of a local object in bytes.

        :param key: Backend-independent logical storage key.
        :returns: Object size in bytes.
        :raises StorageObjectNotFoundError: If the object does not exist.
        :raises StorageReadError: If object metadata cannot be read.
        """
        path = self._resolve_key(key)

        try:
            return path.stat().st_size
        except FileNotFoundError as error:
            raise StorageObjectNotFoundError(
                f"Storage object not found: {key!r}"
            ) from error
        except OSError as error:
            raise StorageReadError(
                f"Unable to read storage object metadata: {key!r}"
            ) from error

    def delete(self, key: str) -> None:
        """Delete an object from local storage.

        :param key: Backend-independent logical storage key.
        :raises NotImplementedError: Always raised until deletion semantics are
            implemented.
        """
        del key

        # Incoming once deletion semantics have been decided, including:
        # - whether missing objects should be ignored or reported
        # - whether deletion should be immediate or deferred
        # - how database and storage deletion failures should be reconciled
        raise NotImplementedError(
            "Persistent media deletion is not implemented yet"
        )

    def _resolve_key(self, key: str) -> Path:
        """Resolve a logical key and ensure it remains beneath the root.

        :param key: Backend-independent logical storage key.
        :returns: Absolute filesystem path for the key.
        :raises InvalidStorageKeyError: If the resolved path escapes the root.
        """
        candidate = (self._root / key).resolve()

        try:
            candidate.relative_to(self._root)
        except ValueError as error:
            raise InvalidStorageKeyError(
                f"Storage key escapes configured root: {key!r}"
            ) from error

        return candidate

    @staticmethod
    def _publish_without_overwrite(
        temporary_path: Path,
        destination: Path,
        key: str,
    ) -> None:
        """Publish a completed temporary file without replacing a target.

        A hard link is used because creating it fails atomically when the
        destination already exists. The temporary file is then removed.

        The temporary file and destination are deliberately created in the
        same directory, ensuring they reside on the same filesystem.

        :param temporary_path: Fully written temporary file path.
        :param destination: Final object path.
        :param key: Logical key used for error messages.
        :raises StorageObjectExistsError: If the destination already exists.
        """
        try:
            os.link(temporary_path, destination)
        except FileExistsError as error:
            raise StorageObjectExistsError(
                f"Storage object already exists: {key!r}"
            ) from error

        temporary_path.unlink()


def _build_storage() -> Storage:
    """Construct persistent storage from application configuration.

    :returns: Application-facing storage instance backed by the configured
        media backend.
    :raises RuntimeError: If the selected media backend configuration is
        missing or unsupported.
    """
    config = get_config()
    media_config = config.media

    if media_config.backend == "local":
        if media_config.local is None:
            raise RuntimeError(
                "Local media configuration is missing"
            )

        backend: StorageBackend = LocalStorageBackend(
            media_config.local.root
        )

    else:
        # Pydantic Literal validation should make this unreachable.
        raise RuntimeError(
            f"Unsupported media backend: "
            f"{media_config.backend!r}"
        )

    return Storage(backend)


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """Return the process-wide persistent media storage instance.

    :returns: Cached application-facing storage instance.
    """
    return _build_storage()
