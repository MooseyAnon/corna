"""Manage working with Corna themes."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import pathlib
from typing import List, Optional, TypeVar

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from typing_extensions import TypedDict
from werkzeug.local import LocalProxy
import yaml

from corna.db import models
from corna.enums import ThemeReviewState
from corna.middleware import alchemy
from corna.utils import get_utc_now, utils
from corna.utils.errors import NoneExistingUserError

THEMES_DIR = utils.CORNA_ROOT / "themes"
ALLOWED_EXTENSIONS = {"html", "css", "js"}

SessionT = TypeVar("SessionT", bound=Session)

logger = logging.getLogger(__name__)


class ThemeError(ValueError):
    """Raised when a theme cannot be resolved."""


# ***** types ******

class Theme(TypedDict):
    """Theme object."""
    name: str
    description: str
    thumbnail: str
    creator: str
    id: str


ThemeList = List[Optional[Theme]]


@dataclass
class ThemeMetadata:
    """Metadata describing a Corna theme.

    Theme metadata is loaded from the ``metadata.yml`` file within a theme
    directory. Page mappings are intentionally arbitrary so themes can support
    additional page types without changes to this class.

    :ivar name: Human-readable name of the theme.
    :ivar creator: Username of the theme creator.
    :ivar description: Description of the theme.
    :ivar thumbnail: Thumbnail filename relative to the theme directory.
    :ivar pages: Mapping of page types to template filenames.
    :ivar error_pages: Mapping of error pages to template filenames.
    """

    name: str
    creator: str
    description: str
    thumbnail: str
    pages: dict[str, str]
    error_pages: dict[str, str]

    @classmethod
    def from_theme_path(cls, theme_path: pathlib.Path) -> "ThemeMetadata":
        """Load theme metadata from a theme directory.

        :param pathlib.Path theme_path: Path to the theme directory containing
            metadata.yml.
        :returns: Parsed theme metadata.
        :rtype: ThemeMetadata
        :raises ThemeError: If required theme metadata is missing.
        """
        metadata_path = theme_path / "metadata.yml"

        with metadata_path.open("r", encoding="utf-8") as metadata_file:
            metadata = yaml.safe_load(metadata_file)

        pages = metadata.get("pages", {})
        error_pages = metadata.get("error_pages", {})

        if "homepage" not in pages:
            raise ThemeError("Theme must define an index page")

        if "default" not in error_pages:
            raise ThemeError("Theme must define a default error page")

        return cls(
            name=metadata["name"],
            creator=metadata["creator"],
            description=metadata["description"],
            thumbnail=metadata["thumbnail"],
            pages=pages,
            error_pages=error_pages,
        )


def sanitize_path(path: str = None) -> Optional[str]:
    """Ensure file path (if given) is legit.

    This function largely exists for debugging later. We
    dont want all errors pass through silently.

    We validate the theme root not a particular theme file exists.
    The only required file is the metadata file.

    :param str path: the path to the main theme file
    :returns: path (if legit)
    :rtype: Optional[str]
    :raises ValueError: if file not found or incorrect file type
    """
    if not path:
        return None

    theme_root: pathlib.Path = THEMES_DIR.resolve()
    expected_dir: pathlib.Path = (theme_root / path).resolve()

    # this ensures the path does not escape the theme directory
    # e.g. `../../<some-dangerous-path>`
    if not expected_dir.is_relative_to(theme_root):
        logging.error("Theme path outside theme directory: %s", path)
        raise ThemeError("Invalid theme path")

    if not expected_dir.exists() or not expected_dir.is_dir():
        raise ThemeError("Theme not found")

    metadata_path = expected_dir / "metadata.yml"

    if not metadata_path.is_file():
        logging.error("No metadata file found: %s", path)
        raise ThemeError("Theme must have a metadata file")

    return path


def create_theme(
    session: LocalProxy,
    creator: str,
    name: str,
    description: Optional[str] = None,
    path: Optional[str] = None,
    thumbnail: Optional[str] = None,
) -> None:
    """This exists to bypass session rules for system bootstrap.

    :param LocalProxy session: database connection
    :param str creator: theme creator
    :param str name: name of theme
    :param Optional[str] description: theme description
    :param Optional[str] path: path to theme html
    :param Optional[str] thumbnail: theme thumbnail url slug. The thumbnail
        must have already been uploaded to the server.

    :raises ValueError: if the user has already made a theme with the
        same name
    """
    user: Optional[models.UserTable] = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == creator)
        .one_or_none()
    )
    if not user:
        raise NoneExistingUserError("Theme creator does not exist")

    # check if user has already created a theme with same name
    # this is a simple way to prevent duplicates
    query = (
        session
        .query(models.Themes)
        .filter(models.Themes.creator_user_id == user.uuid)
        .filter(models.Themes.name == name)
    )

    if session.query(query.exists()).scalar():
        raise ValueError("Theme already exists")

    path: Optional[str] = sanitize_path(path=path)
    status: str = (
        ThemeReviewState.MERGED.value
        if path else
        ThemeReviewState.UNKNOWN.value
    )

    thumnail_uuid: Optional[str] = (
        alchemy.media_uuid(session, thumbnail)
        if thumbnail else None
    )

    session.add(
        models.Themes(
            uuid=utils.get_uuid(),
            created=get_utc_now(),
            name=name,
            description=description,
            path=path,
            status=status,
            creator_user_id=user.uuid,
            thumbnail=thumnail_uuid,
        )
    )


def add(
    session: LocalProxy,
    cookie: str,
    creator: str,
    name: str,
    description: Optional[str] = None,
    path: Optional[str] = None,
    thumbnail: Optional[str] = None,
) -> None:
    """Add a new theme.

    :param LocalProxy session: database connection
    :param str cookie: current user cookie
    :param str creator: theme creator
    :param str name: name of theme
    :param Optional[str] description: theme description
    :param Optional[str] path: path to theme html
    :param Optional[str] thumbnail: theme thumbnail url slug. The thumbnail
        must have already been uploaded to the server.

    :raises NoneExistingUserError: if user session cannot be found
    :raises ValueError: if the user has already made a theme with the
        same name
    """
    # ensure current user is logged in
    # this will be also used as a permissions gate in the future
    utils.current_user(
        session, cookie,
        exception=NoneExistingUserError,
    )

    create_theme(
        session=session,
        creator=creator,
        name=name,
        description=description,
        path=path,
        thumbnail=thumbnail,
    )


def update(session: LocalProxy, cookie: str, data: Theme) -> None:
    """Update theme status.

    This updates the themes status based on PR.

    :param LocalProxy session: database connection
    :param str cookie: current user cookie
    :param Theme data: status information

    :raises NoneExistingUserError: if user session cannot be found
    :raise ValueError: if no theme exists matching query
    :raises ValueError: if multiple themes match details
    """
    # ensure current user is logged in
    # this will be also used as a permissions gate in the future
    utils.current_user(
        session, cookie,
        exception=NoneExistingUserError,
    )

    user: Optional[models.UserTable] = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == data["creator"])
        .one_or_none()
    )
    if not user:
        raise NoneExistingUserError("Theme creator does not exist")

    try:
        theme: Optional[models.Themes] = (
            session
            .query(models.Themes)
            .filter(models.Themes.creator_user_id == user.uuid)
            .filter(models.Themes.name == data["name"])
            .one()
        )

    except NoResultFound:
        raise ValueError(
            "No theme exists matching given details") from NoResultFound

    except MultipleResultsFound:
        raise ValueError(
            "User has multiple themes that match that name, "
            "unable to update") from MultipleResultsFound

    path = sanitize_path(data.get("path"))
    if not path and (data["status"] == ThemeReviewState.MERGED):
        raise ValueError("Cannot set status to merged without valid path")

    prev_status = theme.status
    theme.status = data["status"]

    logger.info(
        "updated status for %s from %s -> %s",
        theme.name, prev_status, theme.status
    )


def thumbnail_url(session: LocalProxy, uuid: str) -> str:
    """Get theme thumbnail URL.

    :param LocalProxy session: db session
    :param str uuid: uuid of the thumbnail
    :returns: a url to the thumbnail image
    :rtype: str
    """
    media: Optional[models.Media] = alchemy.media_from_uuid(session, uuid)

    if not media:
        logger.warning("No theme with uuid %s", uuid)
        return ""

    url: str = (
        f"{utils.UNVERSIONED_API_URL}"
        f"/v1/media/download/{media.url_extension}"
    )
    return url


def creator_(session: LocalProxy, uuid: str) -> str:
    """Get the username of theme creator.

    :param LocalProxy session: db session
    :param str uuid: user uuid
    :returns: username of theme creator
    :rtype: str
    """
    # this return a tuple e.g. ("john_snow",)
    username: Optional[models.UserTable] = (
        session
        .query(models.UserTable.username)
        .filter(models.UserTable.uuid == uuid)
        .one_or_none()
    )

    if not username:
        logger.warning("No user matching uuid %s", uuid)
        return ""

    return username[0]


def get(session: LocalProxy) -> ThemeList:
    """Get all merged and available themes.

    :param LocalProxy session: db session
    :returns: a list of available themes
    :rtype: List[Optional[Dict[str, str]]]
    """
    themes: Optional[models.Themes] = (
        session
        .query(models.Themes)
        .filter(models.Themes.status == ThemeReviewState.MERGED.value)
        .all()
    )

    theme_list: ThemeList = [
        {
            "name": theme.name,
            "description": theme.description,
            "thumbnail": thumbnail_url(session, theme.thumbnail),
            "creator": creator_(session, theme.creator_user_id),
            "id": theme.uuid,
        } for theme in themes]

    return theme_list


def get_theme(session: SessionT, theme_uuid: str) -> pathlib.Path:
    """Return the root path for a theme.

    The theme UUID is resolved against the themes table. The stored path
    represents the root directory of the theme; callers are responsible for
    resolving files within that directory.

    :param SessionT session: Database connection.
    :param str theme_uuid: UUID of the theme to resolve.
    :returns: Root path of the theme.
    :rtype: pathlib.Path
    :raises ThemeError: If the theme cannot be found.
    """
    theme_: Optional[models.Themes] = (
        session
        .query(models.Themes)
        .filter(models.Themes.uuid == theme_uuid)
        .one_or_none()
    )

    if not theme_:
        raise ThemeError(f"Theme not found: {theme_uuid}")

    # full path including theme dir so it can be resolved correctly
    return THEMES_DIR / theme_.path


def get_theme_page(theme_path: pathlib.Path, page: str) -> pathlib.Path:
    """Return the path for a page provided by a theme.

    The page is resolved from the theme's metadata and must exist within the
    theme directory.

    :param pathlib.Path theme_path: Root path of the theme.
    :param str page: Page type to resolve.
    :returns: Path to the requested page.
    :rtype: pathlib.Path
    :raises ThemeError: If the page is not defined, does not exist, or resolves
        outside the theme directory.
    """
    metadata = ThemeMetadata.from_theme_path(theme_path)

    try:
        page_path = metadata.pages[page]
    except KeyError as exc:
        raise ThemeError(
            f"Theme does not define page: {page}"
        ) from exc

    theme_root = theme_path.resolve()
    resolved_path = (theme_root / page_path).resolve()

    if not resolved_path.is_relative_to(theme_root):
        raise ThemeError(
            f"Theme page resolves outside theme directory: {page}"
        )

    if not resolved_path.is_file():
        raise ThemeError(
            f"Theme page does not exist: {resolved_path}"
        )

    return resolved_path


def to_render_path(full_path: pathlib.Path) -> pathlib.Path:
    """Convert a full theme path to a path relative to the themes directory.

    Jinja resolves theme templates relative to ``THEMES_DIR`` rather than from
    their absolute filesystem paths.

    :param pathlib.Path full_path: Full path to a theme template.
    :returns: Template path relative to the themes directory.
    :rtype: pathlib.Path
    :raises ThemeError: If the path is outside the themes directory.
    """
    themes_root = THEMES_DIR.resolve()
    resolved_path = full_path.resolve()

    try:
        return resolved_path.relative_to(themes_root)
    except ValueError as exc:
        raise ThemeError(
            f"Theme path is outside themes directory: {full_path}"
        ) from exc


def get_error_page(theme_path: pathlib.Path, page: str) -> pathlib.Path:
    """Return the error template path for a theme page.

    The requested page is resolved from the theme's error page mapping. If the
    page does not define a specific error template, the theme's default error
    page is used.

    :param pathlib.Path theme_path: Root path of the theme.
    :param str page: Page type associated with the error.
    :returns: Path to the resolved error template.
    :rtype: pathlib.Path
    :raises ThemeError: If the resolved error template does not exist or
        resolves outside the theme directory.
    """
    metadata = ThemeMetadata.from_theme_path(theme_path)

    # fallback on the default error page
    error_page = metadata.error_pages.get(
        page,
        metadata.error_pages["default"],
    )

    theme_root = theme_path.resolve()
    resolved_path = (theme_root / error_page).resolve()

    if not resolved_path.is_relative_to(theme_root):
        raise ThemeError(
            f"Theme error page resolves outside theme directory: {page}"
        )

    if not resolved_path.is_file():
        raise ThemeError(
            f"Theme error page does not exist: {resolved_path}"
        )

    return resolved_path
