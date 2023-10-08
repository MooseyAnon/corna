import logging
import os
from typing import Dict, Optional

from werkzeug.local import LocalProxy

from corna.enums import ThemeReviewState
from corna.db import models
from corna.utils import secure
from corna.utils.errors import NoneExistingUserError
from corna.utils import utils
from corna.utils.utils import CORNA_ROOT

THEMES_DIR = CORNA_ROOT / "themes"
ALLOWED_EXTENSIONS = ["html", "css", "js"]

logger = logging.getLogger(__name__)


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


def add(session: LocalProxy, cookie: str, data: Dict[str, str]) -> None:
    """Add a new theme.

    :param LocalProxy session: database connection
    :param str cookie: current user cookie
    :param dict data: theme information

    :raises NoneExistingUserError: if user session cannot be found
    """
    cookie_id: str = secure.decoded_message(cookie)
    user_session: Optional[models.SessionTable] = (
        session
        .query(models.SessionTable)
        .filter(models.SessionTable.cookie_id == cookie_id)
        .one_or_none()
    )

    if user_session is None:
        raise NoneExistingUserError("Login required for this action")

    if user_session.user.username != data["creator"]:
        user: Optional[models.UserTable] = (
            session
            .query(models.UserTable)
            .filter(models.UserTable.username == data["creator"])
            .one_or_none()
        )
        if not user:
            raise NoneExistingUserError("Theme creator does not exist")

    else:
        user: models.UserTable = user_session.user

    path: Optional[str] = sanitize_path(path=data.get("path"))
    status: str = (
        ThemeReviewState.MERGED.value
        if path else
        ThemeReviewState.UNKNOWN.value
    )

    session.add(
        models.Themes(
            uuid=utils.get_uuid(),
            created=utils.get_utc_now(),
            name=data.get("name"),
            description=data.get("description"),
            path=path,
            status=status,
            creator_user_id=user.uuid
        )
    )
