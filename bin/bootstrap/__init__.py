"""Application bootstrap jobs."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from corna.utils.utils import transactional

from .accounts import bootstrap_accounts
from .avatars import bootstrap_avatars
from .themes import bootstrap_themes


logger = logging.getLogger(__name__)
# Arbitrary application-specific advisory lock identifier.
#
# This value must remain stable so all workers and replicas contend for the
# same PostgreSQL advisory lock.
BOOTSTRAP_LOCK_ID = 6_283_441_001


def try_acquire_lock(session: Session) -> bool:
    """Try to acquire the account-bootstrap lock for this transaction.

    PostgreSQL releases the lock automatically when the surrounding
    transaction commits or rolls back.
    """
    acquired = session.execute(
        text(
            """
            SELECT pg_try_advisory_xact_lock(:lock_id)
            """
        ),
        {
            "lock_id": BOOTSTRAP_LOCK_ID,
        },
    ).scalar_one()

    return bool(acquired)


@transactional
def bootstrap(session: Session) -> bool:
    """Ensure required application-owned data exists.

    Bootstrap uses a non-blocking PostgreSQL advisory lock. When another
    process is already bootstrapping, this process skips the work rather than
    waiting.

    This is safe because the database is the source of truth and bootstrap is
    idempotent. Except during the first deployment against an empty database,
    required bootstrap data will already exist and subsequent executions are
    normally no-ops.

    Returns:
        True if this process acquired the lock and ran the bootstrap jobs.
        False if another process currently holds the bootstrap lock.
    """
    if not try_acquire_lock(session):
        logger.info(
            "Skipping account bootstrap as another process is already running.")
        return False

    accounts_ran = bootstrap_accounts(session)
    avatars_ran = bootstrap_avatars(session)

    return accounts_ran or avatars_ran
