"""Tests for the local persistent-storage backend."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from corna.middleware import storage


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Return an isolated persistent-storage root."""
    return tmp_path / "persistent-media"


@pytest.fixture
def backend(root: Path) -> storage.LocalStorageBackend:
    """Return a local storage backend using an isolated root."""
    return storage.LocalStorageBackend(root)


@pytest.fixture
def store(backend: storage.LocalStorageBackend) -> storage.Storage:
    """Return the application-facing storage façade."""
    return storage.Storage(backend)


def test_local_backend_creates_root_directory(root: Path):
    assert not root.exists()

    storage.LocalStorageBackend(root)

    assert root.exists()
    assert root.is_dir()


def test_local_backend_expands_user_path(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))

    backend = storage.LocalStorageBackend("~/media")

    assert backend._root == (fake_home / "media").resolve()
    assert backend._root.is_dir()


def test_save_file_persists_stream(
    store: storage.Storage,
    root: Path,
):
    key = "images/abc/def/example.jpg"
    content = b"example image bytes"

    store.save_file(
        key,
        io.BytesIO(content),
        content_type="image/jpeg",
    )

    assert (root / key).read_bytes() == content


def test_save_file_creates_parent_directories(
    store: storage.Storage,
    root: Path,
):
    key = "images/abc/def/ghi/example.jpg"

    store.save_file(
        key,
        io.BytesIO(b"content"),
    )

    assert (root / key).is_file()


def test_save_file_resets_seekable_stream(
    store: storage.Storage,
    root: Path,
):
    key = "files/example.bin"
    content = b"complete content"
    stream = io.BytesIO(content)
    stream.seek(5)

    store.save_file(key, stream)

    assert (root / key).read_bytes() == content


def test_failed_write_does_not_leave_destination(
    backend: storage.LocalStorageBackend,
    root: Path,
):
    key = "images/example.jpg"

    class FailingStream:
        def seek(self, offset: int) -> None:
            pass

        def read(self, size: int = -1) -> bytes:
            raise OSError("simulated read failure")

    with pytest.raises(storage.StorageWriteError):
        backend.save_file(
            key,
            FailingStream(),  # type: ignore[arg-type]
        )

    assert not (root / key).exists()


def test_failed_write_removes_temporary_file(
    backend: storage.LocalStorageBackend,
    root: Path,
):
    key = "images/example.jpg"

    class FailingStream:
        def seek(self, offset: int) -> None:
            pass

        def read(self, size: int = -1) -> bytes:
            raise OSError("simulated read failure")

    with pytest.raises(storage.StorageWriteError):
        backend.save_file(
            key,
            FailingStream(),  # type: ignore[arg-type]
        )

    destination_dir = root / "images"

    if destination_dir.exists():
        assert list(destination_dir.glob("*.tmp")) == []
        assert list(destination_dir.glob(".*.tmp")) == []


def test_save_file_rejects_existing_key_by_default(
    store: storage.Storage,
    root: Path,
):
    key = "images/example.jpg"

    store.save_file(key, io.BytesIO(b"first"))

    with pytest.raises(storage.StorageObjectExistsError):
        store.save_file(key, io.BytesIO(b"second"))

    assert (root / key).read_bytes() == b"first"


def test_failed_collision_does_not_leave_temp_file(
    store: storage.Storage,
    root: Path,
):
    key = "images/example.jpg"

    store.save_file(key, io.BytesIO(b"first"))

    with pytest.raises(storage.StorageObjectExistsError):
        store.save_file(key, io.BytesIO(b"second"))

    destination_dir = (root / key).parent

    assert list(destination_dir.iterdir()) == [
        root / key,
    ]


def test_save_file_overwrites_when_explicitly_enabled(
    store: storage.Storage,
    root: Path,
):
    key = "images/example.jpg"

    store.save_file(key, io.BytesIO(b"first"))
    store.save_file(
        key,
        io.BytesIO(b"second"),
        overwrite=True,
    )

    assert (root / key).read_bytes() == b"second"


def test_open_stream_returns_complete_object(
    store: storage.Storage,
):
    key = "videos/example.mp4"
    content = b"0123456789"

    store.save_file(key, io.BytesIO(content))

    with store.open_stream(key) as stream:
        assert stream.read() == content


def test_open_stream_closes_stream_after_context(
    store: storage.Storage,
):
    key = "files/example.bin"

    store.save_file(key, io.BytesIO(b"content"))

    with store.open_stream(key) as stream:
        assert not stream.closed

    assert stream.closed


def test_iter_bytes_returns_complete_object(
    store: storage.Storage,
):
    key = "files/example.bin"
    content = b"abcdefghij"

    store.save_file(key, io.BytesIO(content))

    chunks = list(
        store.iter_bytes(
            key,
            chunk_size=3,
        )
    )

    assert chunks == [
        b"abc",
        b"def",
        b"ghi",
        b"j",
    ]
    assert b"".join(chunks) == content


def test_iter_bytes_reads_inclusive_range(
    store: storage.Storage,
):
    key = "videos/example.mp4"
    content = b"0123456789"

    store.save_file(key, io.BytesIO(content))

    result = b"".join(
        store.iter_bytes(
            key,
            start=2,
            end=6,
            chunk_size=2,
        )
    )

    assert result == b"23456"


def test_iter_bytes_reads_from_start_to_end_of_object(
    store: storage.Storage,
):
    key = "videos/example.mp4"
    content = b"0123456789"

    store.save_file(key, io.BytesIO(content))

    result = b"".join(
        store.iter_bytes(
            key,
            start=4,
            chunk_size=3,
        )
    )

    assert result == b"456789"


def test_iter_bytes_handles_single_byte_range(
    store: storage.Storage,
):
    key = "videos/example.mp4"

    store.save_file(key, io.BytesIO(b"0123456789"))

    result = b"".join(
        store.iter_bytes(
            key,
            start=4,
            end=4,
        )
    )

    assert result == b"4"


def test_size_returns_object_size(
    store: storage.Storage,
):
    key = "images/example.jpg"
    content = b"example-content"

    store.save_file(key, io.BytesIO(content))

    assert store.size(key) == len(content)


def test_size_raises_for_missing_object(
    store: storage.Storage,
):
    with pytest.raises(storage.StorageObjectNotFoundError):
        store.size("images/missing.jpg")


def test_open_stream_raises_for_missing_object(
    store: storage.Storage,
):
    with pytest.raises(storage.StorageObjectNotFoundError):
        with store.open_stream("images/missing.jpg"):
            pass


def test_iter_bytes_raises_for_missing_object(
    store: storage.Storage,
):
    with pytest.raises(storage.StorageObjectNotFoundError):
        list(store.iter_bytes("images/missing.jpg"))


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/absolute/path.jpg",
        "\\absolute\\path.jpg",
        "../outside.jpg",
        "images/../outside.jpg",
        "images/./example.jpg",
        "images//example.jpg",
        "images/example.jpg\x00",
    ],
)
def test_storage_rejects_invalid_keys(
    store: storage.Storage,
    key: str,
):
    with pytest.raises(storage.InvalidStorageKeyError):
        store.save_file(key, io.BytesIO(b"content"))


def test_local_backend_rejects_key_escaping_root(
    backend: storage.LocalStorageBackend,
):
    with pytest.raises(storage.InvalidStorageKeyError):
        backend.save_file(
            "../../outside.jpg",
            io.BytesIO(b"content"),
        )


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1, None),
        (0, -1),
        (None, 5),
        (10, 5),
    ],
)
def test_iter_bytes_rejects_invalid_ranges(
    store: storage.Storage,
    start: int | None,
    end: int | None,
):
    with pytest.raises(ValueError):
        list(
            store.iter_bytes(
                "videos/example.mp4",
                start=start,
                end=end,
            )
        )


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_iter_bytes_rejects_invalid_chunk_size(
    store: storage.Storage,
    chunk_size: int,
):
    with pytest.raises(ValueError):
        list(
            store.iter_bytes(
                "videos/example.mp4",
                chunk_size=chunk_size,
            )
        )


def test_delete_is_not_implemented(
    store: storage.Storage,
):
    with pytest.raises(
        NotImplementedError,
        match="deletion is not implemented",
    ):
        store.delete("images/example.jpg")


def test_get_storage_returns_local_storage():
    result = storage.get_storage()

    assert isinstance(result, storage.Storage)
    assert isinstance(
        result._backend,
        storage.LocalStorageBackend,
    )


def test_get_storage_returns_cached_instance():
    first = storage.get_storage()
    second = storage.get_storage()

    assert first is second


def test_get_storage_uses_configured_local_root(
    _local_persistent_storage: Path,
):
    store = storage.get_storage()
    key = "images/example.jpg"

    store.save_file(
        key,
        io.BytesIO(b"content"),
    )

    assert (
        _local_persistent_storage / key
    ).read_bytes() == b"content"


def test_storage_delegates_save_to_backend(mocker):
    backend = mocker.Mock(spec=storage.StorageBackend)
    store = storage.Storage(backend)
    stream = io.BytesIO(b"content")

    store.save_file(
        "images/example.jpg",
        stream,
        content_type="image/jpeg",
    )

    backend.save_file.assert_called_once_with(
        "images/example.jpg",
        stream,
        content_type="image/jpeg",
        overwrite=False,
    )


def test_save_file_rewinds_seekable_stream(
    store: storage.Storage,
    root: Path,
):
    key = "images/example.jpg"
    content = b"complete-image-content"
    stream = io.BytesIO(content)

    # Simulate hashing/image processing consuming the upload.
    assert stream.read() == content
    assert stream.tell() == len(content)

    store.save_file(key, stream)

    assert (root / key).read_bytes() == content
