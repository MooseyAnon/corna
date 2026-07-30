"""Behavioural tests for the invite approval processor."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from corna.enums import InviteRequestStatus
from corna.db import models
from bin import invite_processor


FROZEN_TIME = "2023-04-29T03:21:34+00:00"

# the code we're testing sits outside of the normal flask loop so the boostrap
# user creation does not run before our tests - it will do so in prod so this
# is only an issue during tests
@pytest.fixture(autouse=True)
def _create_system_user(session):
    user = models.UserTable(
        uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        username="joinbot",
        date_created=FROZEN_TIME,
        number=0,
        is_system_account=True,
        invited_by_user_id=None,
    )

    session.add(user)
    session.flush()


def write_approval_file(
    path,
    *,
    approved=None,
    rejected=None,
):
    """Write an approval queue for a processor test."""
    data = {
        "approved": approved or [],
        "rejected": rejected or [],
    }

    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    return path


def read_approval_file(path):
    """Read the current approval queue."""
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def create_pending_request(
    session,
    *,
    email_address="alice@example.com",
):
    """Insert a pending invite request."""
    request = models.InviteRequestTable(
        uuid=str(uuid.uuid4()),
        email_address=email_address,
        status=InviteRequestStatus.PENDING,
    )

    session.add(request)
    session.commit()

    return request.uuid


def get_request(session, request_id):
    """Reload an invite request after the processor cycle."""
    session.expire_all()

    return (
        session
        .query(models.InviteRequestTable)
        .filter(
            models.InviteRequestTable.uuid == request_id
        )
        .one()
    )


def test_invite_processor__process_cycle_approves_request(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.INVITED
    assert request.invite_id is not None
    assert request.reviewed_at is not None
    assert request.invited_at is not None

    approval_data = read_approval_file(
        approval_file
    )

    assert approval_data == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__process_cycle_creates_valid_invite(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    invite = (
        session
        .query(models.InviteTable)
        .filter(
            models.InviteTable.uuid == str(request.invite_id)
        )
        .one()
    )

    assert invite.created_by_user_id is not None
    assert invite.redeemed_by_user_id is None
    assert invite.redeemed_at is None
    assert invite.revoked_at is None
    assert invite.expires_at > datetime.now(timezone.utc)


def test_invite_processor__process_cycle_rejects_request(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.REJECTED
    assert request.reviewed_at is not None
    assert request.invited_at is None
    assert request.invite_id is None

    approval_data = read_approval_file(
        approval_file
    )

    assert approval_data == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__process_cycle_actions_multiple_requests(
    session,
    tmp_path,
):
    approved_request_id = create_pending_request(
        session,
        email_address="approved@example.com",
    )
    rejected_request_id = create_pending_request(
        session,
        email_address="rejected@example.com",
    )

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=[str(approved_request_id)],
        rejected=[str(rejected_request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    approved_request = get_request(
        session,
        approved_request_id,
    )
    rejected_request = get_request(
        session,
        rejected_request_id,
    )

    assert (
        approved_request.status
        == InviteRequestStatus.INVITED
    )
    assert approved_request.invite_id is not None

    assert (
        rejected_request.status
        == InviteRequestStatus.REJECTED
    )
    assert rejected_request.invite_id is None

    assert read_approval_file(approval_file) == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__missing_approved_request_remains_in_queue(
    session,
    tmp_path,
):
    request_id = uuid.uuid4()

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    assert read_approval_file(approval_file) == {
        "approved": [str(request_id)],
        "rejected": [],
    }


def test_invite_processor__missing_rejected_request_remains_in_queue(
    session,
    tmp_path,
):
    request_id = uuid.uuid4()

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    assert read_approval_file(approval_file) == {
        "approved": [],
        "rejected": [str(request_id)],
    }


def test_invite_processor__reprocessing_already_invited_request_removes_queue_entry(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    first_approval_file = write_approval_file(
        tmp_path / "first.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=first_approval_file,
    )

    first_request = get_request(
        session,
        request_id,
    )
    original_invite_id = first_request.invite_id

    # Simulate the database commit succeeding but the queue-file update being
    # lost or reverted before the next processor cycle.
    retry_approval_file = write_approval_file(
        tmp_path / "retry.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=retry_approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.INVITED
    assert request.invite_id == original_invite_id

    invite_count = (
        session
        .query(models.InviteTable)
        .filter(
            models.InviteTable.uuid == str(original_invite_id)
        )
        .count()
    )

    assert invite_count == 1

    assert read_approval_file(retry_approval_file) == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__reprocessing_already_rejected_request_removes_queue_entry(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    first_approval_file = write_approval_file(
        tmp_path / "first.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=first_approval_file,
    )

    retry_approval_file = write_approval_file(
        tmp_path / "retry.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=retry_approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.REJECTED

    assert read_approval_file(retry_approval_file) == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__rejected_request_cannot_later_be_approved(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    rejection_file = write_approval_file(
        tmp_path / "reject.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=rejection_file,
    )

    approval_file = write_approval_file(
        tmp_path / "approve.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.REJECTED
    assert request.invite_id is None

    # The command was not valid, so it remains available for inspection.
    assert read_approval_file(approval_file) == {
        "approved": [str(request_id)],
        "rejected": [],
    }


def test_invite_processor__invited_request_cannot_later_be_rejected(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "approve.json",
        approved=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    invited_request = get_request(
        session,
        request_id,
    )
    invite_id = invited_request.invite_id

    rejection_file = write_approval_file(
        tmp_path / "reject.json",
        rejected=[str(request_id)],
    )

    invite_processor.process_cycle(
        session,
        approval_file=rejection_file,
    )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.INVITED
    assert request.invite_id == invite_id

    assert read_approval_file(rejection_file) == {
        "approved": [],
        "rejected": [str(request_id)],
    }


def test_invite_processor__invalid_uuid_does_not_change_database_or_file(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=["not-a-uuid"],
    )

    with pytest.raises(
        invite_processor.ApprovalFileError
    ):
        invite_processor.process_cycle(
            session,
            approval_file=approval_file,
        )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.PENDING
    assert request.invite_id is None

    assert read_approval_file(approval_file) == {
        "approved": ["not-a-uuid"],
        "rejected": [],
    }


def test_invite_processor__request_in_both_lists_is_not_processed(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = write_approval_file(
        tmp_path / "invites.json",
        approved=[str(request_id)],
        rejected=[str(request_id)],
    )

    with pytest.raises(
        invite_processor.ApprovalFileError
    ):
        invite_processor.process_cycle(
            session,
            approval_file=approval_file,
        )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.PENDING
    assert request.invite_id is None

    assert read_approval_file(approval_file) == {
        "approved": [str(request_id)],
        "rejected": [str(request_id)],
    }


def test_invite_processor__malformed_json_does_not_change_database(
    session,
    tmp_path,
):
    request_id = create_pending_request(session)

    approval_file = tmp_path / "invites.json"
    approval_file.write_text(
        '{"approved": [',
        encoding="utf-8",
    )

    with pytest.raises(
        invite_processor.ApprovalFileError
    ):
        invite_processor.process_cycle(
            session,
            approval_file=approval_file,
        )

    request = get_request(
        session,
        request_id,
    )

    assert request.status == InviteRequestStatus.PENDING
    assert request.invite_id is None

    assert approval_file.read_text(
        encoding="utf-8"
    ) == '{"approved": ['


def test_invite_processor__empty_queue_has_no_side_effects(
    session,
    tmp_path,
):
    approval_file = write_approval_file(
        tmp_path / "invites.json",
    )

    invite_count_before = (
        session
        .query(models.InviteTable)
        .count()
    )

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    invite_count_after = (
        session
        .query(models.InviteTable)
        .count()
    )

    assert invite_count_after == invite_count_before
    assert read_approval_file(approval_file) == {
        "approved": [],
        "rejected": [],
    }


def test_invite_processor__missing_file_is_created_as_empty_queue(
    session,
    tmp_path,
):
    approval_file = tmp_path / "invites.json"

    assert not approval_file.exists()

    invite_processor.process_cycle(
        session,
        approval_file=approval_file,
    )

    assert approval_file.exists()
    assert read_approval_file(approval_file) == {
        "approved": [],
        "rejected": [],
    }


"""
This is a regression test to ensure our locking is working.
"""
def test_invite_processor__process_cycle_skips_when_lock_is_held(
    session_class,
    tmp_path,
):
    from sqlalchemy import text

    request_session = session_class()
    lock_session = session_class()
    processor_session = session_class()

    try:
        request_id = create_pending_request(
            request_session
        )

        approval_file = write_approval_file(
            tmp_path / "invites.json",
            approved=[str(request_id)],
        )

        lock_acquired = lock_session.execute(
            text(
                """
                SELECT pg_try_advisory_xact_lock(:lock_id)
                """
            ),
            {
                "lock_id": (
                    invite_processor.ADVISORY_LOCK_ID
                ),
            },
        ).scalar_one()

        assert lock_acquired is True

        invite_processor.process_cycle(
            processor_session,
            approval_file=approval_file,
        )

        request = get_request(
            request_session,
            request_id,
        )

        assert (
            request.status
            == models.InviteRequestStatus.PENDING
        )
        assert request.invite_id is None

        assert read_approval_file(approval_file) == {
            "approved": [str(request_id)],
            "rejected": [],
        }

    finally:
        lock_session.rollback()
        processor_session.close()
        lock_session.close()
        request_session.close()
