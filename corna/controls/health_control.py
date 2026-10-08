"""Health checks for the backend service."""

import logging
import pathlib
from typing import TypeVar

from sqlalchemy.orm.scoping import scoped_session as Session

from corna import config, enums, utils
from corna.db import models
from corna.middleware.storage import get_storage

logger = logging.getLogger(__name__)

SessionT = TypeVar("SessionT", bound=Session)


def health_check(session: SessionT) -> tuple[dict, int]:
    """Run application health checks.

    :param SessionT session: db session
    :returns: checks
    :rtype: dict
    """
    checks = {
        "psql": _check_psql(session),
        "s3": _check_s3(session),
        "fs": _check_fs(),
    }

    status = "error" if "error" in checks.values() else "ok"

    # create log entry, we'll use this for debug until we have a dashboard
    if status == "error":
        logger.error("HEALTH FAILURE: checks=%s", checks)

    response = {
        "status": status,
        "checks": checks,
        "time": utils.get_utc_now().isoformat(),
        "service": "corna-api",
    }

    return response


def _check_psql(session: SessionT) -> str:
    """Check that PostgreSQL can query the application schema.

    :param SessionT session: db session
    :returns: "ok" if connection to the db works, else "error". Note: an empty
        row being returned is not a failure here, we only care about being
        able to connect not whatever is in the response.
    :rtype: str
    """
    try:
        session.query(models.TestTable).first()
    except Exception:  # pylint: disable=(broad-exception-caught)
        return "error"

    return "ok"


def _check_s3(session: SessionT) -> str:
    """Check that the configured S3 backend can access an avatar.

    We look for an avatar as uploading avatars is part of the bootstrap process
    so at least one avatar must always exist if the system is up and running
    and the bootstrap process has not failed.

    :param SessionT session: db session
    :returns: "ok", if checks pass. "skipped", if backend is not s3. "error"
        otherwise
    :rtype: bool
    """
    conf = config.get_config()

    if conf.media.backend != "s3":
        return "skipped"

    if not _s3_configured():
        return "error"

    avatar = (
        session
        .query(models.Media)
        .filter(models.Media.type == enums.MediaTypes.AVATAR.value)
        .first()
    )

    if avatar is None:
        return "error"

    try:
        storage = get_storage()
        storage.size(avatar.path)
    except Exception:  # pylint: disable=(broad-exception-caught)
        return "error"

    return "ok"


def _s3_configured() -> bool:
    """Check that the required S3 credentials are configured.

    :returns: Whether the required S3 configuration exists.
    :rtype: bool
    """
    conf = config.get_config()
    s3_config = conf.media.s3

    if s3_config is None:
        return False

    return all(
        (
            s3_config.access_key,
            s3_config.secret_key,
        )
    )


def _check_fs() -> str:
    """Check that the upload temporary directory exists.

    :returns: "ok", if the directory exists else "error"
    :rtype: str
    """
    conf = config.get_config()
    upload_tmp_dir = pathlib.Path(conf.app.upload_tmp_dir)

    if not upload_tmp_dir.is_dir():
        return "error"

    return "ok"
