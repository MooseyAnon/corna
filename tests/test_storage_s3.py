"""Tests for the S3 persistent-storage backend."""

from __future__ import annotations

import io
from typing import BinaryIO

import pytest
from botocore.exceptions import ClientError

from corna.middleware import storage


@pytest.fixture
def s3_client(mocker):
    return mocker.Mock()


@pytest.fixture
def backend(s3_client):
    return storage.S3StorageBackend(
        bucket="corna-test-media",
        region="eu-west-2",
        client=s3_client,
    )


@pytest.fixture
def store(backend):
    return storage.Storage(backend)


def client_error(
    *,
    operation: str,
    code: str,
    status: int,
) -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": code,
                "Message": code,
            },
            "ResponseMetadata": {
                "HTTPStatusCode": status,
            },
        },
        operation,
    )


def test_save_file_puts_object_without_overwrite(
    store,
    s3_client,
):
    stream = io.BytesIO(b"image-content")

    store.save_file(
        "images/example.jpg",
        stream,
        content_type="image/jpeg",
    )

    s3_client.put_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="images/example.jpg",
        Body=stream,
        ContentType="image/jpeg",
        IfNoneMatch="*",
    )


def test_save_file_omits_content_type_when_unknown(
    store,
    s3_client,
):
    stream = io.BytesIO(b"content")

    store.save_file(
        "files/example.bin",
        stream,
    )

    s3_client.put_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="files/example.bin",
        Body=stream,
        IfNoneMatch="*",
    )


def test_save_file_allows_explicit_overwrite(
    store,
    s3_client,
):
    stream = io.BytesIO(b"replacement")

    store.save_file(
        "images/example.jpg",
        stream,
        overwrite=True,
    )

    s3_client.put_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="images/example.jpg",
        Body=stream,
    )


def test_save_file_rewinds_stream(
    store,
    s3_client,
):
    stream = io.BytesIO(b"complete-content")
    stream.read()

    store.save_file(
        "files/example.bin",
        stream,
    )

    assert stream.tell() == 0


def test_save_file_maps_precondition_failure_to_exists(
    store,
    s3_client,
):
    s3_client.put_object.side_effect = client_error(
        operation="PutObject",
        code="PreconditionFailed",
        status=412,
    )

    with pytest.raises(
        storage.StorageObjectExistsError,
    ):
        store.save_file(
            "images/example.jpg",
            io.BytesIO(b"content"),
        )


def test_save_file_maps_conditional_conflict_to_write_error(
    store,
    s3_client,
):
    s3_client.put_object.side_effect = client_error(
        operation="PutObject",
        code="ConditionalRequestConflict",
        status=409,
    )

    with pytest.raises(storage.StorageWriteError):
        store.save_file(
            "images/example.jpg",
            io.BytesIO(b"content"),
        )


def test_iter_bytes_reads_complete_object(
    store,
    s3_client,
    mocker,
):
    body = mocker.Mock()
    body.read.side_effect = [
        b"abc",
        b"def",
        b"",
    ]

    s3_client.get_object.return_value = {
        "Body": body,
    }

    result = b"".join(
        store.iter_bytes(
            "files/example.bin",
            chunk_size=3,
        )
    )

    assert result == b"abcdef"

    s3_client.get_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="files/example.bin",
    )

    body.close.assert_called_once_with()


def test_iter_bytes_forwards_inclusive_range(
    store,
    s3_client,
    mocker,
):
    body = mocker.Mock()
    body.read.side_effect = [
        b"234",
        b"56",
    ]

    s3_client.get_object.return_value = {
        "Body": body,
    }

    result = b"".join(
        store.iter_bytes(
            "videos/example.mp4",
            start=2,
            end=6,
            chunk_size=3,
        )
    )

    assert result == b"23456"

    s3_client.get_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="videos/example.mp4",
        Range="bytes=2-6",
    )

    body.close.assert_called_once_with()


def test_iter_bytes_forwards_open_ended_range(
    store,
    s3_client,
    mocker,
):
    body = mocker.Mock()
    body.read.side_effect = [
        b"456",
        b"789",
        b"",
    ]

    s3_client.get_object.return_value = {
        "Body": body,
    }

    result = b"".join(
        store.iter_bytes(
            "videos/example.mp4",
            start=4,
            chunk_size=3,
        )
    )

    assert result == b"456789"

    s3_client.get_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="videos/example.mp4",
        Range="bytes=4-",
    )


def test_size_uses_head_object(
    store,
    s3_client,
):
    s3_client.head_object.return_value = {
        "ContentLength": 1234,
    }

    result = store.size("images/example.jpg")

    assert result == 1234

    s3_client.head_object.assert_called_once_with(
        Bucket="corna-test-media",
        Key="images/example.jpg",
    )


@pytest.mark.parametrize(
    "operation",
    [
        "get_object",
        "head_object",
    ],
)
def test_missing_object_is_translated(
    store,
    s3_client,
    operation,
):
    getattr(s3_client, operation).side_effect = client_error(
        operation=operation,
        code="NoSuchKey",
        status=404,
    )

    with pytest.raises(
        storage.StorageObjectNotFoundError,
    ):
        if operation == "get_object":
            list(
                store.iter_bytes(
                    "images/missing.jpg"
                )
            )
        else:
            store.size("images/missing.jpg")
