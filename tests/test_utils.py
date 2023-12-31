import datetime

from freezegun import freeze_time
import pytest

from corna.utils import encodings, future, secure, utils

FROZEN_TIME = "2023-04-05T03:21:34"


def test_signing_similar_messages():

    m1 = "aaaaaaaaa"
    m2 = "aaaaaaaab"

    s1 = secure.sign(m1)
    s2 = secure.sign(m2)

    _, _, s1_sig = secure.unsign(s1)
    _, _, s2_sig = secure.unsign(s2)

    assert secure.verify(m1, s1_sig)
    assert secure.verify(m2, s2_sig)

    assert not secure.verify(m1, s2_sig)
    assert not secure.verify(m2, s1_sig)


@freeze_time(FROZEN_TIME)
def test_unsign():

    sig = secure.sign("aaaaaaaaa")
    _, orig_message, _ = secure.unsign(sig)
    assert orig_message == b"aaaaaaaaa"


@freeze_time(FROZEN_TIME)
def test_expiry_in_unsign():
    
    sig = secure.sign("aaaaaaaaa")
    expiry, _, _ = secure.unsign(sig)
    # signing adds 14 days to original datetime by default
    assert expiry == b"2023-04-19T03:21:34+00:00"


def test_fake_message():
    message = "I am a fake message"
    assert secure.verify(message, encodings.base64_encode(message)) == False


@freeze_time(FROZEN_TIME)
@pytest.mark.parametrize("days", [2, 4, 14, 23, -1, -3])
def test_future(days):

    days_skipped = 5 + days
    expected = datetime.datetime(
        2023, 4, days_skipped, 3, 21, 34,
        tzinfo=datetime.timezone.utc
    )
    assert future(days) == expected


@freeze_time(FROZEN_TIME)
@pytest.mark.parametrize("date,expected",
    [
        ("2023-04-04T03:21:34+00:00", True),
        ("2023-04-05T01:21:34+00:00", True),
        ("2023-04-05T03:20:34+00:00", True),
        ("2023-04-05T03:21:34+01:00", True),
        ("2023-03-05T03:21:34+00:00", True),
        ("2023-04-06T03:21:34+00:00", False),
        ("2023-04-05T04:21:34+00:00", False),
        ("2023-04-05T03:22:34+00:00", False),
        ("2023-04-05T03:21:34-01:00", False),
    ]
)
def test_expiry_2(date, expected):
    assert secure.expired(date) == expected
