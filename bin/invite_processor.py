#!/usr/bin/env python3
"""Process manually approved and rejected Corna invite requests.

Expected approval file:

{
    "approved": [
        "<invite-request-uuid>"
    ],
    "rejected": [
        "<invite-request-uuid>"
    ]
}

The file acts as a small command queue rather than a copy of the database
lifecycle state.

Successfully processed entries are removed from the file. Entries that cannot
be processed remain in place so they can be inspected or retried.

PostgreSQL remains the source of truth for whether a request is pending,
invited, or rejected.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from corna.controls import auth_control
from corna.enums import InviteRequestStatus
from corna.utils import secure, utils
from corna.db import models


logger = logging.getLogger(__name__)


APPROVAL_FILE = Path(
    os.environ.get(
        "CORNA_INVITE_APPROVAL_FILE",
        "/approvals/invites.json",
    )
)

POLL_INTERVAL_SECONDS = int(
    os.environ.get(
        "CORNA_INVITE_PROCESSOR_INTERVAL",
        "30",
    )
)

# Arbitrary application-level advisory-lock identifier. This must remain stable
# across all processor instances.
ADVISORY_LOCK_ID = 8_619_024_117

APPROVAL_KEYS = (
    "approved",
    "rejected",
)


class ApprovalFileError(RuntimeError):
    """Raised when the approval file is malformed."""


def empty_approval_file() -> dict[str, list[str]]:
    """Return an empty approval queue."""
    return {
        "approved": [],
        "rejected": [],
    }


def validate_unique_membership(
    data: dict[str, list[str]],
) -> None:
    """Ensure a request does not appear in both decision lists."""
    approved = set(data["approved"])
    rejected = set(data["rejected"])

    duplicates = approved & rejected

    if duplicates:
        raise ApprovalFileError(
            "Invite requests cannot be both approved and rejected: "
            f"{sorted(duplicates)}"
        )


def read_approval_file(
    path: Path,
) -> dict[str, list[str]]:
    """Read and validate the approval queue."""
    if not path.exists():
        return empty_approval_file()

    try:
        raw_data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise ApprovalFileError(
            f"Invalid JSON in approval file {path}: {error}"
        ) from error

    if not isinstance(raw_data, dict):
        raise ApprovalFileError(
            "Approval file must contain a JSON object."
        )

    unexpected_keys = set(raw_data) - set(APPROVAL_KEYS)

    if unexpected_keys:
        raise ApprovalFileError(
            "Approval file contains unexpected keys: "
            f"{sorted(unexpected_keys)}"
        )

    data: dict[str, list[str]] = {}

    for key in APPROVAL_KEYS:
        values = raw_data.get(key, [])

        if not isinstance(values, list):
            raise ApprovalFileError(
                f"Approval field {key!r} must be a list."
            )

        if not all(isinstance(value, str) for value in values):
            raise ApprovalFileError(
                f"Approval field {key!r} must contain strings."
            )

        # Preserve ordering while removing duplicate UUIDs from the same list.
        data[key] = list(dict.fromkeys(values))

    validate_unique_membership(data)

    return data


def write_approval_file(
    path: Path,
    data: dict[str, list[str]],
) -> None:
    """Atomically rewrite the approval queue."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_name(
        f".{path.name}.tmp"
    )

    contents = json.dumps(
        data,
        indent=4,
    )

    temporary_path.write_text(
        f"{contents}\n",
        encoding="utf-8",
    )

    # Path.replace() atomically replaces the destination when the temporary
    # file and destination are on the same filesystem.
    temporary_path.replace(path)


def parse_request_id(
    value: str,
) -> UUID:
    """Parse an invite-request UUID from the approval queue."""
    try:
        return UUID(value)
    except ValueError as error:
        raise ApprovalFileError(
            f"Invalid invite-request UUID: {value!r}"
        ) from error


def try_acquire_lock(
    session: Session,
) -> bool:
    """Try to acquire the processor transaction's advisory lock."""
    return bool(
        session.execute(
            text(
                "SELECT pg_try_advisory_xact_lock(:lock_id)"
            ),
            {
                "lock_id": ADVISORY_LOCK_ID,
            },
        ).scalar_one()
    )


def get_request(
    session: Session,
    # these are UUIDs from json, _not_ from the system or psql
    # we typically save UUIDs as strings so we need to convert it here
    request_id: UUID,
) -> models.InviteRequestTable | None:
    """Get and lock an invite request row."""
    return (
        session
        .query(models.InviteRequestTable)
        .filter(
            models.InviteRequestTable.uuid == str(request_id)
        )
        .with_for_update()
        .one_or_none()
    )


def get_joinbot(
    session: Session,
) -> models.UserTable:
    """Return the system account used to issue approved invites."""
    return (
        session
        .query(models.UserTable)
        .filter(
            models.UserTable.username == "joinbot",
            models.UserTable.is_system_account.is_(True),
        )
        .one()
    )


def approve_request(
    session: Session,
    request_id: UUID,
    *,
    joinbot: models.UserTable,
) -> bool:
    """Issue an invite for a pending request.

    Returns True when the queue entry may be removed.

    Requests already in the invited state are treated as complete. This allows
    the processor to recover when the database committed successfully but the
    approval file was not rewritten before the process stopped.
    """
    invite_request = get_request(
        session,
        request_id,
    )

    if invite_request is None:
        logger.warning(
            "Invite request does not exist: request_id=%s",
            request_id,
        )
        return False

    if (
        invite_request.status
        == InviteRequestStatus.INVITED
    ):
        return True

    if (
        invite_request.status
        != InviteRequestStatus.PENDING
    ):
        logger.warning(
            "Cannot approve invite request in state %s: "
            "request_id=%s",
            invite_request.status.value,
            request_id,
        )
        return False

    token = auth_control.create_invite_for_user(
        session,
        joinbot.uuid,
    )

    # create_invite_for_user returns the raw token rather than the ORM object.
    # Resolve the created invite using its deterministic token hash.
    token_hash = secure.hash_invite_token(token)

    invite = (
        session
        .query(models.InviteTable)
        .filter(
            models.InviteTable.token_hash == token_hash
        )
        .one()
    )

    now = datetime.now(timezone.utc)

    invite_request.status = (
        InviteRequestStatus.INVITED
    )
    invite_request.reviewed_at = now
    invite_request.invited_at = now
    invite_request.invite_id = invite.uuid

    session.flush()

    # Replace this log entry with the outbound email implementation later.
    logger.info(
        "Invite issued: request_id=%s email=%s join_path=/join/%s",
        invite_request.uuid,
        invite_request.email_address,
        token,
    )

    return True


def reject_request(
    session: Session,
    request_id: UUID,
) -> bool:
    """Reject a pending invite request.

    Returns True when the queue entry may be removed.
    """
    invite_request = get_request(
        session,
        request_id,
    )

    if invite_request is None:
        logger.warning(
            "Invite request does not exist: request_id=%s",
            request_id,
        )
        return False

    if (
        invite_request.status
        == InviteRequestStatus.REJECTED
    ):
        return True

    if (
        invite_request.status
        != InviteRequestStatus.PENDING
    ):
        logger.warning(
            "Cannot reject invite request in state %s: "
            "request_id=%s",
            invite_request.status.value,
            request_id,
        )
        return False

    invite_request.status = (
        InviteRequestStatus.REJECTED
    )
    invite_request.reviewed_at = datetime.now(
        timezone.utc
    )

    session.flush()

    logger.info(
        "Invite request rejected: request_id=%s email=%s",
        invite_request.uuid,
        invite_request.email_address,
    )

    return True


def remove_processed_entries(
    entries: list[str],
    processed: set[str],
) -> list[str]:
    """Remove successfully processed UUIDs while preserving file order."""
    return [
        request_id
        for request_id in entries
        if request_id not in processed
    ]


def process_cycle(
    session: Session,
    *,
    approval_file: Path = APPROVAL_FILE,
) -> None:
    """Run one approval-processing cycle."""
    if not try_acquire_lock(session):
        session.rollback()

        logger.debug(
            "Another invite processor holds the advisory lock; "
            "skipping cycle."
        )
        return

    data = read_approval_file(
        approval_file
    )

    processed_approved: set[str] = set()
    processed_rejected: set[str] = set()

    approved_ids = [
        (
            request_id_text,
            parse_request_id(request_id_text),
        )
        for request_id_text in data["approved"]
    ]

    rejected_ids = [
        (
            request_id_text,
            parse_request_id(request_id_text),
        )
        for request_id_text in data["rejected"]
    ]

    joinbot = None

    if approved_ids:
        joinbot = get_joinbot(session)

    for request_id_text, request_id in approved_ids:
        if approve_request(
            session,
            request_id,
            joinbot=joinbot,
        ):
            processed_approved.add(
                request_id_text
            )

    for request_id_text, request_id in rejected_ids:
        if reject_request(
            session,
            request_id,
        ):
            processed_rejected.add(
                request_id_text
            )

    data["approved"] = remove_processed_entries(
        data["approved"],
        processed_approved,
    )

    data["rejected"] = remove_processed_entries(
        data["rejected"],
        processed_rejected,
    )

    session.commit()

    # The database is committed before the file is rewritten. If the process
    # stops between these operations, the next cycle recognises already
    # invited or rejected rows and removes them from the queue.
    write_approval_file(
        approval_file,
        data,
    )


def run_forever(
    session_factory: Any,
    *,
    approval_file: Path = APPROVAL_FILE,
    poll_interval: int = POLL_INTERVAL_SECONDS,
) -> None:
    """Poll the approval queue indefinitely."""
    while True:
        session = session_factory()

        try:
            process_cycle(
                session,
                approval_file=approval_file,
            )
        except ApprovalFileError:
            session.rollback()

            logger.exception(
                "Invite approval file is invalid."
            )
        except Exception:
            session.rollback()

            logger.exception(
                "Invite processing cycle failed."
            )
        finally:
            session.close()

        time.sleep(poll_interval)


def main() -> None:
    """Start the invite processor."""
    logging.basicConfig(
        level=os.environ.get(
            "LOG_LEVEL",
            "INFO",
        ),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    from corna.db import session_maker

    session_factory = session_maker(
        application_name="corna-invite-processor",
        statement_timeout_secs=30,
    )

    run_forever(session_factory)


if __name__ == "__main__":
    main()
