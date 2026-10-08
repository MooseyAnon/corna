"""Tests for health endpoints."""

from http import HTTPStatus

from freezegun import freeze_time
import pytest
import yaml

from corna import enums
from corna.config import get_config
from corna.controls import health_control
from corna.db import models


FROZEN_TIME = "2026-10-07T03:21:34+00:00"
AVATAR_PATH = "avatars/health-check-avatar.png"


@pytest.fixture
def health_config(local_config):
    """Configure an isolated local or S3 backend for a health test."""

    def configure(backend):
        config_data = yaml.safe_load(
            local_config.read_text(encoding="utf-8")
        )

        if backend == "s3":
            config_data["media"] = {
                "backend": "s3",
                "s3": {
                    "bucket": "corna-test-media",
                    "region": "eu-west-2",
                    "endpoint_url": None,
                    "use_signed_urls": False,
                    "signed_url_ttl": 300,
                },
            }

        local_config.write_text(
            yaml.safe_dump(config_data, sort_keys=False),
            encoding="utf-8",
        )
        get_config.cache_clear()

        return get_config()

    get_config.cache_clear()
    yield configure
    get_config.cache_clear()


def add_avatar(session):
    """Add an avatar that the S3 health check can probe."""
    session.add(
        models.Media(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            url_extension="health-check-avatar",
            original_filename="health-check-avatar.png",
            path=AVATAR_PATH,
            type=enums.MediaTypes.AVATAR.value,
            orphaned=False,
        )
    )
    session.commit()


def assert_health_response(response, *, status_code, checks):
    """Assert the complete health endpoint contract."""
    expected_status = (
        "ok" if status_code == HTTPStatus.OK else "error"
    )

    assert response.status_code == status_code
    assert response.json == {
        "checks": checks,
        "service": "corna-api",
        "status": expected_status,
        "time": FROZEN_TIME,
    }


def test_ping(client):
    """Test the shallow health endpoint."""
    response = client.get("/api/v1/ping")

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"status": "ok"}


@freeze_time(FROZEN_TIME)
def test_healthz_local_ok(client, health_config):
    """Report healthy when local dependencies are available."""
    config = health_config("local")
    config.app.upload_tmp_dir.mkdir()

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.OK,
        checks={
            "psql": "ok",
            "s3": "skipped",
            "fs": "ok",
        },
    )


@freeze_time(FROZEN_TIME)
def test_healthz_missing_upload_directory(client, health_config):
    """Report unhealthy when the upload directory is unavailable."""
    health_config("local")

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        checks={
            "psql": "ok",
            "s3": "skipped",
            "fs": "error",
        },
    )


@freeze_time(FROZEN_TIME)
def test_healthz_database_unavailable(client, session, health_config):
    """Report unhealthy when the application schema cannot be queried."""
    config = health_config("local")
    config.app.upload_tmp_dir.mkdir()
    models.TestTable.__table__.drop(bind=session.bind)

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        checks={
            "psql": "error",
            "s3": "skipped",
            "fs": "ok",
        },
    )


@freeze_time(FROZEN_TIME)
def test_healthz_s3_ok(
    client,
    session,
    mocker,
    health_config,
):
    """Report healthy when the configured S3 backend is available."""
    mocker.patch("corna.utils.vault_item", return_value="random-string")

    config = health_config("s3")
    config.app.upload_tmp_dir.mkdir()

    add_avatar(session)

    # mock s3 bucket
    s3_storage = mocker.Mock()
    mocker.patch.object(health_control, "get_storage", return_value=s3_storage)

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.OK,
        checks={
            "psql": "ok",
            "s3": "ok",
            "fs": "ok",
        },
    )
    s3_storage.size.assert_called_once_with(AVATAR_PATH)


@freeze_time(FROZEN_TIME)
def test_healthz_s3_unavailable(
    client,
    session,
    mocker,
    health_config,
):
    """Report unhealthy when the configured S3 backend cannot be read."""
    mocker.patch("corna.utils.vault_item", return_value="random-string")

    config = health_config("s3")
    config.app.upload_tmp_dir.mkdir()

    add_avatar(session)

    # mock s3 bucket
    s3_storage = mocker.Mock()
    s3_storage.size.side_effect = OSError("S3 unavailable")

    mocker.patch.object(health_control, "get_storage", return_value=s3_storage)

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        checks={
            "psql": "ok",
            "s3": "error",
            "fs": "ok",
        },
    )
    # this is the step that fails, everything before this should pass
    s3_storage.size.assert_called_once_with(AVATAR_PATH)


@freeze_time(FROZEN_TIME)
def test_healthz_s3_no_tokens(
    client,
    session,
    mocker,
    health_config,
):
    """No access tokens for S3."""
    mocker.patch("corna.utils.vault_item", return_value="")

    config = health_config("s3")
    config.app.upload_tmp_dir.mkdir()

    # mock s3 to ensure we never actually call it
    s3_storage = mocker.Mock()
    mocker.patch.object(health_control, "get_storage", return_value=s3_storage)

    response = client.get("/api/v1/healthz")

    assert_health_response(
        response,
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        checks={
            "psql": "ok",
            "s3": "error",
            "fs": "ok",
        },
    )
    # this should never be called as we fail before we reach the size call
    s3_storage.size.assert_not_called()
