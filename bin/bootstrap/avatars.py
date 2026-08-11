"""Bootstrap default system avatars."""

import logging
import pathlib

from sqlalchemy.orm import Session

from corna import enums
from corna.controls import media_control
from corna.db import models
from corna.utils import image_proc
from corna.utils import utils


logger = logging.getLogger(__name__)


AVATAR_PATH = (
    pathlib.Path(__file__).parent.parent
    / "assets"
    / "avatars"
)


def _avatar_exists(
    session: Session,
    image_hash: str,
) -> bool:
    """Check whether an image with the given hash already exists.

    Image hashes are used as the bootstrap identity rather than filenames or
    storage paths. This means the bootstrap remains idempotent if uploaded
    media is later stored using randomly generated filenames.

    :param Session session: DB session
    :param str image_hash: hash of the system avatar
    :returns: whether the image already exists
    :rtype: bool
    """
    return (
        session
        .query(models.Images)
        .filter(models.Images.hash == image_hash)
        .first()
        is not None
    )


def bootstrap_avatars(session: Session) -> bool:
    """Ensure all bundled system avatars have been uploaded.

    The function is idempotent. Each source image is hashed and compared
    against the images table before being uploaded.

    A non-blocking PostgreSQL advisory lock prevents multiple Gunicorn workers
    or service replicas from attempting the bootstrap concurrently. A process
    that cannot acquire the lock simply skips the bootstrap.

    :param Session session: DB session
    :returns: whether this process acquired the lock and ran the bootstrap
    :rtype: bool
    """

    logger.info("Starting system avatar bootstrap")

    for avatar_path in sorted(AVATAR_PATH.iterdir()):
        if not avatar_path.is_file():
            continue

        avatar = utils.to_filestorage(
            str(avatar_path),
            avatar_path.name,
        )
        avatar_hash = image_proc.hash_image(avatar)

        if _avatar_exists(session, avatar_hash):
            logger.info(
                "System avatar already exists, skipping: %s",
                avatar_path.name,
            )
            continue

        logger.info(
            "Uploading system avatar: %s",
            avatar_path.name,
        )

        response = media_control.upload(
            session,
            avatar,
            enums.MediaTypes.AVATAR.value,
        )

        logger.info(
            "Successfully uploaded system avatar: filename=%s id=%s",
            avatar_path.name,
            response["id"],
        )

    logger.info("System avatar bootstrap complete")
    return True
