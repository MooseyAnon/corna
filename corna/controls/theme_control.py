"""Manage working with Corna themes."""

import logging
import os
from typing import Optional

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from typing_extensions import TypedDict
from werkzeug.datastructures import FileStorage
from werkzeug.local import LocalProxy

from corna.db import models
from corna.enums import ThemeReviewState
from corna.utils import get_utc_now, image_proc, secure, utils
from corna.utils.errors import NoneExistingUserError

THEMES_DIR = utils.CORNA_ROOT / "themes"
ALLOWED_EXTENSIONS = {"html", "css", "js"}

logger = logging.getLogger(__name__)


# ***** types ******

class _Required(TypedDict):
    """Required fields across all types."""

    creator: str
    name: str


class Theme(_Required, total=False):
    """Type for a single theme"""

    description: str
    path: str
    status: str
    thumbnail: FileStorage


def is_allowed(filename: str) -> bool:
    """Check if file extension is valid.

    This is lifted straight out of the flask docs for handling
    file upload.

    :param str filename: the name of the file being uploaded
    :return: True if extension is valid
    :rtype: bool
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_path(path: str = None) -> Optional[str]:
    """Ensure file path (if given) is legit.

    This function largely exists for debugging later. We
    dont want all errors pass through silently.

    :param str path: the path to the main theme file
    :returns: path (if legit)
    :rtype: Optional[str]
    :raises ValueError: if file not found or incorrect file type
    """
    if not path:
        return None

    if not (THEMES_DIR / path).exists():
        raise ValueError("Theme not in directory")

    if not is_allowed(path):
        logging.error("incorrect file type attempt: %s", path)
        raise ValueError("Incorrect file type")

    return path


def add(session: LocalProxy, cookie: str, data: Theme) -> None:
    """Add a new theme.

    :param LocalProxy session: database connection
    :param str cookie: current user cookie
    :param dict data: theme information

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

    user: Optional[models.UserTable] = (
        session
        .query(models.UserTable)
        .filter(models.UserTable.username == data["creator"])
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
        .filter(models.Themes.name == data["name"])
    )

    if session.query(query.exists()).scalar():
        raise ValueError("Theme already exists")

    path: Optional[str] = sanitize_path(path=data.get("path"))
    status: str = (
        ThemeReviewState.MERGED.value
        if path else
        ThemeReviewState.UNKNOWN.value
    )

    thumbnail_: Optional[str] = data.get("thumbnail")
    thumnail_uuid: Optional[str] = (
        thumbnail(session, thumbnail_)
        if thumbnail_ else
        None
    )

    session.add(
        models.Themes(
            uuid=utils.get_uuid(),
            created=get_utc_now(),
            name=data.get("name"),
            description=data.get("description"),
            path=path,
            status=status,
            creator_user_id=user.uuid,
            thumbnail=thumnail_uuid,
        )
    )


def thumbnail(session: LocalProxy, image: FileStorage) -> str:
    """Handle saving thumbnail to disk and DB.

    :param LocalProxy session: a db session
    :param FileStorage image: image to save as thumbnail
    :returns: image uuid
    :rtype: str
    """
    path: str = image_proc.save(image)
    thumbnail_uuid: str = utils.get_uuid()
    url_extension: str = secure.generate_unique_token(
        session=session,
        column=models.Images.url_extension,
        func=utils.random_short_string
    )
    session.add(
        models.Images(
            uuid=thumbnail_uuid,
            path=path,
            size=os.stat(path).st_size,
            created=get_utc_now(),
            url_extension=url_extension,
            orphaned=False,
        )
    )

    return thumbnail_uuid


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
