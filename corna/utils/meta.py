"""Meta utils i.e. utils that are also used but other utils.

This is here to avoid circular dependencies while also avoiding
unnecessary code duplication.
"""

import datetime
import logging
import pathlib
from typing import Union

logger = logging.Logger(__name__)


def get_utc_now() -> datetime.datetime:
    """Get a time-zone aware datetime for "now".

    :returns: "now" as a datetime
    :rtype: datetime.datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def future(days: int = 14) -> datetime.datetime:
    """Datetime object for some number of days in the future.

    :param int days: number of days in the future
    :returns: current time + number of skip days
    :rtype: datetime.datetime
    """
    now = get_utc_now()
    skip = datetime.timedelta(days=days)
    return now + skip


def mkdir(path: Union[pathlib.Path, str], exists_ok: bool = True) -> None:
    """Recursively make directories in a path.

    Note: this is only here to make logging a bit cleaner.

    :param pathlib.Path path: path or directory to make
    :param bool exists_ok: Its useful to overwrite the exists_ok option
        when attempting to do existence checks during directory creation.
    :raises FileExistsError: when ran with exists_ok=False and the dir
        exists.
    """
    if not isinstance(path, pathlib.Path):
        logger.warning(
            "path must a pathlib.Path object, attempting to convert"
        )
        path: pathlib.Path = pathlib.Path(path)

    # attempt to recursively make path
    path.mkdir(parents=True, exist_ok=exists_ok)
