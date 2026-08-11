from bin.bootstrap import bootstrap
from bin.bootstrap import avatars
from corna import enums
from corna.db import models
from corna.utils import image_proc, utils


def test_bootstrap_accounts_is_idempotent(session):
    first_ran = bootstrap(session)
    second_ran = bootstrap(session)

    assert first_ran is True
    assert second_ran is True

    usernames = {
        username
        for username, in (
            session
            .query(models.UserTable.username)
            .filter(
                models.UserTable.is_system_account.is_(True),
            )
            .all()
        )
    }

    assert usernames == {
        "themebot",
        "joinbot",
        "avatarbot",
    }

    assert (
        session
        .query(models.UserTable)
        .filter(
            models.UserTable.is_system_account.is_(True),
        )
        .count()
    ) == 3

    # ensure no emails were made
    assert session.query(models.EmailTable).count() == 0


def test_bootstrap_creates_system_avatars(session):
    """Bootstrap uploads all bundled system avatars."""
    bootstrap(session)

    expected_count = len([
        path
        for path in avatars.AVATAR_PATH.iterdir()
        if path.is_file()
    ])

    uploaded_avatars = (
        session
        .query(models.Media)
        .filter(
            models.Media.type == enums.MediaTypes.AVATAR.value,
        )
        .all()
    )

    assert len(uploaded_avatars) == expected_count

    # Ensure every bundled avatar hash exists in the images table.
    persisted_hashes = {
        image_hash
        for image_hash, in (
            session
            .query(models.Images.hash)
            .all()
        )
    }

    for avatar_path in avatars.AVATAR_PATH.iterdir():
        if not avatar_path.is_file():
            continue

        avatar = utils.to_filestorage(
            str(avatar_path),
            avatar_path.name,
        )

        assert image_proc.hash_image(avatar) in persisted_hashes


def test_bootstrap_skips_existing_system_avatars(session_class):
    """Running bootstrap repeatedly does not duplicate system avatars."""
    first_session = session_class()
    bootstrap(first_session)

    original_media_count = (
        first_session
        .query(models.Media)
        .filter(
            models.Media.type == enums.MediaTypes.AVATAR.value,
        )
        .count()
    )

    original_image_count = (
        first_session
        .query(models.Images)
        .count()
    )
    first_session.close()

    second_session = session_class()
    bootstrap(second_session)

    assert (
        second_session
        .query(models.Media)
        .filter(
            models.Media.type == enums.MediaTypes.AVATAR.value,
        )
        .count()
        == original_media_count
    )

    assert (
        second_session
        .query(models.Images)
        .count()
        == original_image_count
    )
    second_session.close()
