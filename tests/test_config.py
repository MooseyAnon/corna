from pathlib import Path

from pydantic import ValidationError
import pytest
import yaml

from corna import config


@pytest.fixture(autouse=True)
def _clear_config_state(monkeypatch):
    monkeypatch.setenv("CONFIG_FILE_PATH", "i-do-not-exist.yml")

    # Prevent cached configuration leaking between tests.
    from corna.config import get_config

    get_config.cache_clear()

    yield

    get_config.cache_clear()


def _mock_config(
    *,
    upload_dir: str,
    backend: str = "local",
    with_placeholder: bool = False,
    local_root: str = "./tmp-assets",
) -> dict:
    """Return valid example configuration data."""
    database_name = "${DB_NAME}" if with_placeholder else "corna_dev"

    config_data = {
        "database": {
            "address": "localhost",
            "user": "cornauser",
            "port": 5432,
            "name": database_name,
            "ssl_mode": None,
        },
        "vault": {
            "path": "~/vault",
            "password_file": "~/.vault-password",
        },
        "app": {
            "debug": True,
            "port": 5000,
            "sqlalchemy_echo": True,
            "upload_tmp_dir": upload_dir,
            "max_file_size": 10_485_760,
            "allowed_extensions": [
                "gif",
                "jpg",
                "jpeg",
                "png",
                "webp",
                "mp4",
                "mov",
            ],
            "api_base_url": "http://localhost:5000",
        },
    }

    if backend == "local":
        config_data["media"] = {
            "backend": "local",
            "local": {
                "root": local_root,
            },
        }
    elif backend == "s3":
        config_data["media"] = {
            "backend": "s3",
            "s3": {
                "bucket": "corna-test-media",
                "region": "eu-west-2",
                "endpoint_url": None,
                "access_key": "test-access-key",
                "secret_key": "test-secret-key",
                "use_signed_urls": False,
                "signed_url_ttl": 300,
            },
        }
    else:
        raise ValueError(f"Unsupported test backend: {backend}")

    return config_data


@pytest.fixture
def temp_config_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    upload_dir = tmp_path / "uploads"
    config_path.write_text(
        yaml.safe_dump(
            _mock_config(
                local_root=str(tmp_path / "media"),
                upload_dir=str(upload_dir)
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    return config_path


@pytest.fixture
def temp_s3_config_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    upload_dir = tmp_path / "uploads"
    config_path.write_text(
        yaml.safe_dump(
            _mock_config(backend="s3", upload_dir=str(upload_dir)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    return config_path


def test_config_loads_local_backend_from_yaml(tmp_path, temp_config_file):
    test_config = config.load_config(temp_config_file)

    expected_workdir = tmp_path / "uploads"

    assert test_config.database.address == "localhost"
    assert test_config.database.user == "cornauser"
    assert test_config.database.port == 5432
    assert test_config.database.name == "corna_dev"
    assert test_config.database.ssl_mode is None

    assert test_config.vault.path == "~/vault"
    assert test_config.vault.password_file == "~/.vault-password"

    assert test_config.app.debug is True
    assert test_config.app.port == 5000
    assert test_config.app.sqlalchemy_echo is True
    assert test_config.app.upload_tmp_dir == expected_workdir
    assert test_config.app.max_file_size == 10_485_760
    assert test_config.app.allowed_extensions == [
        "gif",
        "jpg",
        "jpeg",
        "png",
        "webp",
        "mp4",
        "mov",
    ]
    assert test_config.app.api_base_url == "http://localhost:5000"

    assert test_config.media.backend == "local"
    assert test_config.media.local is not None
    assert test_config.media.s3 is None
    assert test_config.media.local.root == temp_config_file.parent / "media"
    assert test_config.media.local.root.is_dir()


def test_config_loads_s3_backend_from_yaml(temp_s3_config_file):
    test_config = config.load_config(temp_s3_config_file)

    assert test_config.media.backend == "s3"
    assert test_config.media.local is None
    assert test_config.media.s3 is not None

    assert test_config.media.s3.bucket == "corna-test-media"
    assert test_config.media.s3.region == "eu-west-2"
    assert test_config.media.s3.endpoint_url is None
    assert test_config.media.s3.access_key == "test-access-key"
    assert test_config.media.s3.secret_key == "test-secret-key"
    assert test_config.media.s3.use_signed_urls is False
    assert test_config.media.s3.signed_url_ttl == 300


def test_load_config_uses_config_file_path(
    temp_config_file,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONFIG_FILE_PATH",
        str(temp_config_file),
    )

    test_config = config.load_config()

    assert test_config.database.name == "corna_dev"


def test_load_config_fails_without_path(monkeypatch):
    monkeypatch.delenv("CONFIG_FILE_PATH", raising=False)

    with pytest.raises(
        RuntimeError,
        match="No configuration file specified",
    ):
        config.load_config()


def test_config_expands_environment_placeholder(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DB_NAME", "placeholder_value")

    config_path = tmp_path / "config.yaml"
    upload_dir = tmp_path / "uploads"
    config_path.write_text(
        yaml.safe_dump(
            _mock_config(
                with_placeholder=True,
                local_root=str(tmp_path / "media"),
                upload_dir=str(upload_dir),
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    test_config = config.load_config(config_path)

    assert test_config.database.name == "placeholder_value"


def test_missing_environment_placeholder_becomes_empty_string(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("DB_NAME", raising=False)

    config_path = tmp_path / "config.yaml"
    upload_dir = tmp_path / "uploads"
    config_path.write_text(
        yaml.safe_dump(
            _mock_config(
                with_placeholder=True,
                local_root=str(tmp_path / "media"),
                upload_dir=str(upload_dir),
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        config.load_config(config_path)


def test_config_fails_when_file_does_not_exist(tmp_path):
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(
        FileNotFoundError,
        match="Configuration file not found",
    ):
        config.load_config(missing_path)


def test_config_fails_for_unsupported_file_type(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("example = true", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Unsupported configuration file format",
    ):
        config.load_config(config_path)


def test_config_fails_when_path_is_directory(tmp_path):
    with pytest.raises(
        ValueError,
        match="Configuration path is not a file",
    ):
        config.load_config(tmp_path)


def test_local_backend_requires_local_config(tmp_path):
    config_data = _mock_config(
        local_root=str(tmp_path / "media"),
        upload_dir=str(tmp_path / "uploads"),
    )
    config_data["media"] = {
        "backend": "local",
    }

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="media.local must be configured",
    ):
        config.load_config(config_path)


def test_s3_backend_requires_s3_config(tmp_path):
    config_data = _mock_config(
        local_root=str(tmp_path / "media"),
        upload_dir=str(tmp_path / "uploads"),
    )
    config_data["media"] = {
        "backend": "s3",
    }

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="media.s3 must be configured",
    ):
        config.load_config(config_path)


def test_local_backend_rejects_s3_config(tmp_path):
    config_data = _mock_config(
        local_root=str(tmp_path / "media"),
        upload_dir= str(tmp_path / "uploads"),
    )
    config_data["media"]["s3"] = {
        "bucket": "unexpected",
        "region": "eu-west-2",
        "access_key": "key",
        "secret_key": "secret",
    }

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="media.s3 must not be configured",
    ):
        config.load_config(config_path)


def test_s3_backend_rejects_local_config(tmp_path):
    config_data = _mock_config(backend="s3", upload_dir=str(tmp_path / "uploads"))
    config_data["media"]["local"] = {
        "root": str(tmp_path / "media"),
    }

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="media.local must not be configured",
    ):
        config.load_config(config_path)


@pytest.mark.parametrize(
    "missing_field",
    [
        "bucket",
        "region",
        "access_key",
        "secret_key",
    ],
)
def test_s3_backend_requires_mandatory_fields(
    tmp_path,
    missing_field,
):
    config_data = _mock_config(backend="s3", upload_dir=str(tmp_path / "uploads"))
    del config_data["media"]["s3"][missing_field]

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        config.load_config(config_path)


def test_unknown_configuration_field_is_rejected(tmp_path):
    config_data = _mock_config(
        local_root=str(tmp_path / "media"),
        upload_dir=str(tmp_path / "uploads")
    )
    config_data["app"]["sqlalchemy_ecoh"] = True

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match="sqlalchemy_ecoh",
    ):
        config.load_config(config_path)


def test_get_config_is_cached(
    temp_config_file,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONFIG_FILE_PATH",
        str(temp_config_file),
    )

    first = config.get_config()
    second = config.get_config()

    assert first is second
