"""Bootstrap required Corna system accounts."""

import logging

from sqlalchemy.orm import Session

from corna.utils import get_utc_now, utils
from corna.db import models


logger = logging.getLogger(__name__)


SYSTEM_ACCOUNTS = (
    "themebot",
    "joinbot",
    "avatarbot",
)


class BootstrapError(RuntimeError):
    """Raised when existing data conflicts with the required bootstrap state."""


def ensure_system_account(
    session: Session,
    username: str,
) -> models.UserTable:
    """Ensure that a reserved system account exists.

    Existing normal users are never silently converted into system accounts.
    """

    user = (
        session
        .query(models.UserTable)
        .filter(
            models.UserTable.username == username,
        )
        .one_or_none()
    )

    if user is not None:
        if not user.is_system_account:
            raise BootstrapError(
                "Reserved system username belongs to a normal user: "
                f"{username}"
            )

        return user

    user = models.UserTable(
        uuid=utils.get_uuid(),
        username=username,
        date_created=get_utc_now(),
        is_system_account=True,
        invited_by_user_id=None,
    )

    session.add(user)
    session.flush()

    return user


def bootstrap_accounts(session: Session) -> bool:
    """Create all required system accounts.

    Returns:
        True when this process acquired the lock and checked the accounts.
        False when another process currently owns the bootstrap lock.
    """

    for username in SYSTEM_ACCOUNTS:
        ensure_system_account(
            session,
            username,
        )

        logger.info("Created account for user '%s'", username)

    return True
