from bin.bootstrap import bootstrap
from corna.db import models


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
