"""Application bootstrap jobs."""

from sqlalchemy.orm import Session

from corna.utils.utils import transactional

from .accounts import bootstrap_accounts


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
    return bootstrap_accounts(session)
