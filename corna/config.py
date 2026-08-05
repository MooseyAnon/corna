"""Configuration management for the Corna application."""
# pylint: disable=cyclic-import
from __future__ import annotations

from functools import cache
import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel, ConfigDict, Field, field_validator, model_validator)
import yaml


class DatabaseConfig(BaseModel):
    """Database connection settings.

    :ivar address: Hostname or IP address of the PostgreSQL server.
    :ivar user: PostgreSQL username.
    :ivar port: PostgreSQL port.
    :ivar name: PostgreSQL database name.
    :ivar ssl_mode: Optional PostgreSQL SSL mode.
    """

    address: str
    user: str
    port: int
    name: str
    ssl_mode: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("ssl_mode", mode="before")
    @classmethod
    def empty_ssl_mode_is_none(cls, value: str | None) -> str | None:
        """Treat an empty SSL mode as unset.

        :param value: Raw SSL mode value from the configuration source.
        :returns: `None` for empty strings, otherwise the original value.
        :rtype: str | None
        """
        if value == "":
            return None

        return value

    @property
    def url(self) -> str:
        """Build the database connection URL.

        :returns: PostgreSQL connection URL including the vault password.
        :rtype: str
        """
        # Import lazily to avoid the config <-> vault module import cycle.
        # This is safe because vault access happens only after configuration
        # loading has completed.
        #
        # C0415=import-outside-toplevel
        from corna.utils import vault_item  # pylint: disable=C0415

        password = vault_item(f"postgres.{self.user}")

        url = (
            f"postgresql://{self.user}:{password}"
            f"@{self.address}:{self.port}/{self.name}"
        )

        if self.ssl_mode:
            url = f"{url}?sslmode={self.ssl_mode}"

        return url

    @property
    def connection_details(self) -> str:
        """Return safe database connection details for logging.

        :returns: PostgreSQL connection URL with the password redacted.
        :rtype: str
        """
        url = (
            f"postgresql://{self.user}:*****"
            f"@{self.address}:{self.port}/{self.name}"
        )

        if self.ssl_mode:
            url = f"{url}?sslmode={self.ssl_mode}"

        return url


class VaultConfig(BaseModel):
    """Ansible Vault settings.

    :ivar path: Path to the encrypted vault file.
    :ivar password_file: Path to the file containing the vault password.
    """

    path: str
    password_file: str

    model_config = ConfigDict(extra="forbid")


class LocalMediaConfig(BaseModel):
    """Local media storage settings.

    :ivar root: Directory used to store uploaded media files.
    """

    root: Path

    model_config = ConfigDict(extra="forbid")

    @field_validator("root")
    @classmethod
    def ensure_root_exists(cls, root: Path) -> Path:
        """Create the configured media root when it does not exist.

        :param root: Configured local media root directory.
        :returns: The original root path after ensuring it exists.
        :rtype: Path
        """
        root.mkdir(parents=True, exist_ok=True)
        return root


class S3MediaConfig(BaseModel):
    """S3-compatible media storage settings.

    :ivar bucket: S3 bucket name.
    :ivar region: S3 region name.
    :ivar access_key: S3 access key ID.
    :ivar secret_key: S3 secret access key.
    :ivar endpoint_url: Optional custom S3-compatible endpoint URL.
    :ivar use_signed_urls: Whether generated media URLs should be signed.
    :ivar signed_url_ttl: Signed URL lifetime in seconds.
    """

    bucket: str
    region: str
    access_key: str
    secret_key: str
    endpoint_url: str | None = None
    use_signed_urls: bool = False
    signed_url_ttl: int = 300

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "bucket",
        "region",
        "access_key",
        "secret_key",
    )
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        """Reject empty required S3 values.

        :param value: Required S3 configuration value.
        :returns: The stripped value.
        :rtype: str
        :raises ValueError: If the stripped value is empty.
        """
        value = value.strip()

        if not value:
            raise ValueError("Value must not be empty")

        return value

    @field_validator("signed_url_ttl")
    @classmethod
    def signed_url_ttl_must_be_positive(cls, value: int) -> int:
        """Require a positive signed URL lifetime.

        :param value: Signed URL lifetime in seconds.
        :returns: The validated lifetime.
        :rtype: int
        :raises ValueError: If the lifetime is less than or equal to zero.
        """
        if value <= 0:
            raise ValueError("signed_url_ttl must be greater than zero")

        return value


class MediaConfig(BaseModel):
    """Media storage settings.

    :ivar backend: Selected media backend, either `local` or `s3`.
    :ivar local: Local backend configuration when `backend` is `local`.
    :ivar s3: S3 backend configuration when `backend` is `s3`.
    """

    backend: Literal["local", "s3"]
    local: LocalMediaConfig | None = None
    s3: S3MediaConfig | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_selected_backend(self) -> MediaConfig:
        """Require exactly the configuration used by the selected backend.

        :returns: The validated media configuration.
        :rtype: MediaConfig
        :raises ValueError: If the selected backend configuration is missing
            or an unused backend configuration is present.
        """
        if self.backend == "local":
            if self.local is None:
                raise ValueError(
                    "media.local must be configured when "
                    "media.backend is 'local'"
                )

            if self.s3 is not None:
                raise ValueError(
                    "media.s3 must not be configured when "
                    "media.backend is 'local'"
                )

        if self.backend == "s3":
            if self.s3 is None:
                raise ValueError(
                    "media.s3 must be configured when "
                    "media.backend is 's3'"
                )

            if self.local is not None:
                raise ValueError(
                    "media.local must not be configured when "
                    "media.backend is 's3'"
                )

        return self


class AppConfig(BaseModel):
    """Application runtime settings.

    :ivar debug: Whether debug mode is enabled.
    :ivar port: HTTP port used by the application.
    :ivar upload_tmp_dir: Temporary directory used during uploads.
    :ivar api_base_url: Public base URL for API routes.
    :ivar sqlalchemy_echo: Whether SQLAlchemy should log SQL statements.
    :ivar max_file_size: Maximum accepted upload size in bytes.
    :ivar allowed_extensions: Allowed upload file extensions without dots.
    """

    debug: bool
    port: int
    upload_tmp_dir: Path
    api_base_url: str

    sqlalchemy_echo: bool = False
    max_file_size: int = 20 * 1024 * 1024  # 20BM
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            "gif",
            "jpg",
            "jpeg",
            "png",
            "webp",
            "mp4",
            "mov",
        ]
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("port")
    @classmethod
    def port_must_be_valid(cls, value: int) -> int:
        """Validate the application port.

        :param value: Configured TCP port.
        :returns: The validated port.
        :rtype: int
        :raises ValueError: If the port is outside the valid TCP range.
        """
        if not 1 <= value <= 65_535:
            raise ValueError("port must be between 1 and 65535")

        return value

    @field_validator("max_file_size")
    @classmethod
    def max_file_size_must_be_positive(cls, value: int) -> int:
        """Require a positive maximum upload size.

        :param value: Maximum upload size in bytes.
        :returns: The validated maximum upload size.
        :rtype: int
        :raises ValueError: If the size is less than or equal to zero.
        """
        if value <= 0:
            raise ValueError("max_file_size must be greater than zero")

        return value

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def split_extensions(cls, value: Any) -> Any:
        """Support either a YAML list or comma-separated string.

        :param value: Raw extension configuration value.
        :returns: A list for comma-separated strings, otherwise the original
            value.
        """
        if isinstance(value, str):
            return [
                extension.strip()
                for extension in value.split(",")
                if extension.strip()
            ]

        return value

    @field_validator("allowed_extensions")
    @classmethod
    def normalise_extensions(cls, values: list[str]) -> list[str]:
        """Normalise extensions to lowercase without leading dots.

        :param values: Configured upload extensions.
        :returns: Normalised upload extensions.
        :rtype: list[str]
        :raises ValueError: If no non-empty extensions remain.
        """
        extensions = [
            value.strip().lower().removeprefix(".")
            for value in values
            if value.strip()
        ]

        if not extensions:
            raise ValueError("allowed_extensions must not be empty")

        return extensions

    @field_validator("upload_tmp_dir")
    @classmethod
    def ensure_upload_dir_exists(cls, root: Path) -> Path:
        """Create the configured upload directory when it does not exist.

        :param root: Configured upload temporary directory.
        :returns: The original path after ensuring it exists.
        :rtype: Path
        """
        root.mkdir(parents=True, exist_ok=True)
        return root


class Config(BaseModel):
    """Complete Corna application configuration.

    :ivar app: Application runtime settings.
    :ivar database: Database connection settings.
    :ivar media: Media storage settings.
    :ivar vault: Ansible Vault settings.
    """

    app: AppConfig
    database: DatabaseConfig
    media: MediaConfig
    vault: VaultConfig

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_file(cls, config_path: str | Path) -> Config:
        """Load and validate configuration from YAML or JSON.

        :param config_path: Path to a YAML or JSON configuration file.

        :returns: Validated application configuration.
        :rtype: Config
        :raises FileNotFoundError: If the configuration file does not exist.
        :raises ValueError: If the path is not a file, uses an unsupported
            suffix, or does not contain an object at its root.
        """
        path = Path(config_path).expanduser()

        if not path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Configuration path is not a file: {path}"
            )

        match path.suffix.lower():
            case ".yml" | ".yaml":
                data = cls._load_yaml(path)
            case ".json":
                data = cls._load_json(path)
            case suffix:
                raise ValueError(
                    f"Unsupported configuration file format: {suffix}"
                )

        processed_data = cls._process_env_placeholders(data)

        if not isinstance(processed_data, dict):
            raise ValueError(
                "The configuration file must contain an object "
                "at its root"
            )

        return cls.model_validate(processed_data)

    @staticmethod
    def _load_yaml(config_path: Path) -> Any:
        """Read configuration data from YAML.

        :param config_path: Path to the YAML configuration file.
        :returns: Parsed YAML data.
        :rtype: Any
        """
        with config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    @staticmethod
    def _load_json(config_path: Path) -> Any:
        """Read configuration data from JSON.

        :param config_path: Path to the JSON configuration file.
        :returns: Parsed JSON data.
        :rtype: Any
        """
        with config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def _process_env_placeholders(cls, data: Any) -> Any:
        """Process environment variable placeholders in configuration data.

        Values matching `${NAME}` are replaced with the value of the
        matching environment variable.

        :param data: Configuration data to process recursively.
        :returns: Configuration data with environment placeholders resolved.
        :rtype: Any
        :raises ValueError: If a referenced environment variable is unset.
        """
        if isinstance(data, dict):
            return {
                key: cls._process_env_placeholders(value)
                for key, value in data.items()
            }

        if isinstance(data, list):
            return [
                cls._process_env_placeholders(item)
                for item in data
            ]

        if (
            isinstance(data, str)
            and data.startswith("${")
            and data.endswith("}")
        ):
            env_var = data[2:-1]

            value = os.getenv(env_var)
            if value is None:
                raise ValueError(
                    f"Environment variable '{env_var}' is required "
                    "by the configuration but is not set."
                )

            return value

        return data

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration into serialisable values.

        :returns: JSON-serialisable configuration mapping.
        :rtype: dict
        """
        return self.model_dump(mode="json")

    def to_yaml(self) -> str:
        """Serialise the configuration as YAML.

        :returns: YAML representation of the configuration.
        :rtype: str
        """
        return yaml.safe_dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
        )

    def save_yaml(self, file_path: str | Path) -> None:
        """Save the configuration as YAML.

        :param file_path: Destination YAML file path.
        """
        path = Path(file_path).expanduser()

        with path.open("w", encoding="utf-8") as file:
            file.write(self.to_yaml())


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from an explicit path or ``CONFIG_FILE_PATH``.

    :param config_path: Optional explicit configuration file path.

    :returns: Validated application configuration.
    :rtype: Config
    :raises RuntimeError: If no path is provided and ``CONFIG_FILE_PATH`` is
        unset.
    """
    resolved_path = config_path or os.environ.get("CONFIG_FILE_PATH")

    if not resolved_path:
        raise RuntimeError(
            "No configuration file specified. Set CONFIG_FILE_PATH "
            "or pass config_path explicitly."
        )

    return Config.from_file(resolved_path)


# Lazily load and cache the config once per process.
# The config is immutable for a given service version.
#
# Keeping it behind a function makes it easy to mock in tests.
@cache
def get_config() -> Config:
    """Return the cached application configuration.

    :returns: Process-wide cached application configuration.
    :rtype: Config
    """
    return load_config()
