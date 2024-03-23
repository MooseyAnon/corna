"""Manage working with Corna themes."""

import logging
from typing import List, Optional

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

class Theme(TypedDict):
    """Theme object."""
    name: str
    description: str
    thumbnail: str
    creator: str
    id: str


ThemeList = List[Optional[Theme]]


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


def add(
    session: LocalProxy,
    cookie: str,
    creator: str,
    name: str,
    description: Optional[str] = None,
    path: Optional[str] = None,
    thumbnail_blob: Optional[FileStorage] = None,
) -> None:
    """Add a new theme.

    :param LocalProxy session: database connection
    :param str cookie: current user cookie
    :param str creator: theme creator
    :param str name: name of theme
    :param Optional[str] description: theme description
    :param Optional[str] path: path to theme html
    :param Optional[FileStorage] thumbnail_blob: theme thumbnail

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
        thumbnail(session, thumbnail_blob)
        if thumbnail_blob else
        None
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
            size=image_proc.size(path),
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


def thumbnail_url(session: LocalProxy, uuid: str) -> str:
    """Get theme thumbnail URL.

    :param LocalProxy session: db session
    :param str uuid: uuid of the thumbnail
    :returns: a url to the thumbnail image
    :rtype: str
    """
    # this returns a tuple e.g. ("abcdef",)
    url_extension: Optional[models.Images] = (
        session
        .query(models.Images.url_extension)
        .filter(models.Images.uuid == uuid)
        .one_or_none()
    )

    if not url_extension:
        logger.warning("No theme with uuid %s", uuid)
        return ""

    url: str = (
        f"{utils.UNVERSIONED_API_URL}"
        f"/v1/media/download/{url_extension[0]}"
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
