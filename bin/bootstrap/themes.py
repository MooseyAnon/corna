"""Bootstrap bundled system themes."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy.orm import Session

from corna import enums
from corna.db import models
from corna.controls import media_control, theme_control
from corna.utils import utils


logger = logging.getLogger(__name__)


# Directory names relative to the configured themes directory.
SYSTEM_THEMES = (
    "pinterested-in-men",
)


class ThemeMetadataError(ValueError):
    """Raised when bundled theme metadata is invalid."""


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load metadata for a bundled system theme.

    :param Path metadata_path: path to the theme metadata file
    :returns: parsed theme metadata
    :rtype: dict
    :raises ThemeMetadataError: if required metadata is missing or invalid
    """
    try:
        with metadata_path.open("r", encoding="utf-8") as metadata_file:
            metadata = yaml.safe_load(metadata_file)
    except (OSError, yaml.YAMLError) as error:
        raise ThemeMetadataError(
            f"Unable to read theme metadata: {metadata_path}"
        ) from error

    if not isinstance(metadata, dict):
        raise ThemeMetadataError(
            f"Theme metadata must contain a mapping: {metadata_path}"
        )

    required_fields = {
        "name",
        "creator",
    }

    missing_fields = required_fields - metadata.keys()

    if missing_fields:
        raise ThemeMetadataError(
            "Theme metadata is missing required fields "
            f"{sorted(missing_fields)}: {metadata_path}"
        )

    return metadata


def _theme_exists(
    session: Session,
    *,
    creator: str,
    name: str,
) -> bool:
    """Check whether a system theme has already been registered.

    Themes are uniquely identified by the combination of their creator and
    display name, matching the invariant enforced by theme creation.

    :param Session session: DB session
    :param str creator: username of the theme creator
    :param str name: theme display name
    :returns: whether the theme already exists
    :rtype: bool
    """
    user = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == creator)
        .one_or_none()
    )

    if user is None:
        return False

    query = (
        session
        .query(models.Themes)
        .filter(models.Themes.creator_user_id == user.uuid)
        .filter(models.Themes.name == name)
    )

    return bool(
        session.query(query.exists()).scalar()
    )


def _upload_thumbnail(
    session: Session,
    thumbnail_path: Path,
) -> str:
    """Upload a bundled theme thumbnail.

    :param Session session: DB session
    :param Path thumbnail_path: path to the thumbnail image
    :returns: url extension of the uploaded media
    :rtype: str
    """
    thumbnail = utils.to_filestorage(
        str(thumbnail_path),
        thumbnail_path.name,
    )

    response = media_control.upload(
        session,
        thumbnail,
        # the default themes we save a big files. If we pass this as a
        # thumbnail the size wont be reduced to a manageable size
        enums.MediaTypes.IMAGE.value,
    )

    logger.info(
        "Successfully uploaded system theme thumbnail: "
        "filename=%s extension=%s",
        thumbnail_path.name,
        response["url_extension"],
    )

    return response["url_extension"]


def _bootstrap_theme(
    session: Session,
    *,
    themes_path: Path,
    theme_directory_name: str,
) -> bool:
    """Bootstrap a single bundled system theme.

    :param Session session: DB session
    :param Path themes_path: root directory containing themes
    :param str theme_directory_name: theme directory relative to themes root
    :returns: whether the theme was created
    :rtype: bool
    """
    theme_path = themes_path / theme_directory_name
    metadata_path = theme_path / "metadata.yml"

    if not theme_path.is_dir():
        raise ThemeMetadataError(
            f"System theme directory does not exist: {theme_path}"
        )

    metadata = _load_metadata(metadata_path)

    creator = metadata["creator"]
    name = metadata["name"]

    if _theme_exists(
        session,
        creator=creator,
        name=name,
    ):
        logger.info(
            "System theme already exists, skipping: "
            "creator=%s name=%s",
            creator,
            name,
        )
        return False


    index_path = theme_path / metadata["pages"]["homepage"]

    if not index_path.is_file():
        raise ThemeMetadataError(
            f"System theme has no index.html: {theme_path}"
        )

    thumbnail_extension: Optional[str] = None
    thumbnail_filename = metadata.get("thumbnail")

    if thumbnail_filename is not None:
        thumbnail_path = theme_path / thumbnail_filename

        if not thumbnail_path.is_file():
            raise ThemeMetadataError(
                "System theme thumbnail does not exist: "
                f"{thumbnail_path}"
            )

        thumbnail_extension = _upload_thumbnail(
            session,
            thumbnail_path,
        )

    logger.info(
        "Registering system theme: creator=%s name=%s path=%s",
        creator,
        name,
        theme_directory_name,
    )

    theme_control.create_theme(
        session,
        creator=creator,
        name=name,
        description=metadata.get("description"),
        path=theme_directory_name,
        thumbnail=thumbnail_extension,
    )

    logger.info(
        "Successfully registered system theme: "
        "creator=%s name=%s",
        creator,
        name,
    )

    return True


def bootstrap_themes(
    session: Session,
) -> bool:
    """Ensure all bundled system themes are registered.

    The caller owns the bootstrap transaction and advisory lock. Existing
    themes are skipped using the creator/name uniqueness invariant, making
    repeated bootstrap execution idempotent.

    :param Session session: DB session
    :param Path themes_path: root directory containing bundled themes
    :returns: whether at least one theme was created
    :rtype: bool
    """
    logger.info("Starting system theme bootstrap")

    created = False

    for theme_directory_name in SYSTEM_THEMES:
        if _bootstrap_theme(
            session,
            themes_path=theme_control.THEMES_DIR,
            theme_directory_name=theme_directory_name,
        ):
            created = True

    logger.info(
        "System theme bootstrap complete: created=%s",
        created,
    )

    return created
