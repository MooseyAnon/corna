import datetime
import pathlib

from freezegun import freeze_time
import pytest

from corna.utils import encodings, future, image_proc, mkdir, secure, utils, vault_item
from corna.utils.vault_manager import VaultError
from tests import shared_data

FROZEN_TIME = "2023-04-05T03:21:34"


@freeze_time(FROZEN_TIME)
def test_signing_end_to_end():
    message = "aaaaaaaaa"
    signed = secure.sign(message)

    assert secure.is_valid(signed)


@freeze_time(FROZEN_TIME)
def test_tampering_with_expiry_date_fails_signature():
    message = "aaaaaaaaa"

    signed = secure.sign(message)
    _, _, sig = secure.unsign(signed)

    # create fake payload by tampering with expiry
    tampered = "2023-04-06T03:21:34||aaaaaaaaa"
    assert not secure.verify(tampered, sig)

    # check legit payload just to make sure happy path works
    legit = "2023-04-19T03:21:34+00:00||aaaaaaaaa"
    assert secure.verify(legit, sig)


@freeze_time(FROZEN_TIME)
def test_signing_similar_messages():

    m1 = "aaaaaaaaa"
    m2 = "aaaaaaaab"

    s1 = secure.sign(m1)
    s2 = secure.sign(m2)

    _, _, s1_sig = secure.unsign(s1)
    _, _, s2_sig = secure.unsign(s2)

    # the message changes when being signed, we append the expiry to it
    # Note: future() currently adds 14 days to "todays" date
    assert secure.verify(b"2023-04-19T03:21:34+00:00||aaaaaaaaa", s1_sig)
    assert secure.verify(b"2023-04-19T03:21:34+00:00||aaaaaaaab", s2_sig)

    assert not secure.verify(b"2023-04-19T03:21:34+00:00||aaaaaaaaa", s2_sig)
    assert not secure.verify(b"2023-04-19T03:21:34+00:00||aaaaaaaab", s1_sig)


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


@pytest.mark.parametrize("dirty_html,expected_fragment", [
    # XSS attempts - should strip or neutralize
    ("<img src=x onerror=alert(1)>", "<img>"),
    ('<a href="javascript:alert(1)">link</a>', '<a rel="noopener noreferrer">link</a>'),
    ('<a onmouseover="alert(1)">hover</a>', '<a rel="noopener noreferrer">hover</a>'),
    ('<script>alert("XSS")</script>', ''),
    (r'<IMG """><SCRIPT>alert("XSS")</SCRIPT>"\>', r'<img>"\&gt;'),

    # Valid HTML - should preserve
    ('<b>bold</b>', '<b>bold</b>'),
    ('<i>italic</i>', '<i>italic</i>'),
    ('<a href="https://example.com">link</a>', '<a href="https://example.com" rel="noopener noreferrer">link</a>'),

    # img tags must only contain our API url
    ('<img src="https://example.com/img.png">', '<img>'),
    # this from testing config in conftest. We're using it to verify the
    # behaviour but in prod this will be replaced with the legit url
    ('<img src="http://api.localhost">', '<img src="http://api.localhost">'),

    # Invalid but allowed tag+attribute - should strip attribute
    ('<img src="invalid-url">', '<img>'),
    ('<a href="not a url">click</a>', '<a rel="noopener noreferrer">click</a>'),

    # Escaped HTML should stay escaped
    ('<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>', '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>'),

    # Non-allowed tags should be stripped
    ('<video src="x.mp4"></video>', ''),
    ('<iframe src="https://evil.com"></iframe>', ''),
])
def test_clean_html(dirty_html, expected_fragment, local_config):
    cleaned = utils.clean_html(dirty_html)
    assert expected_fragment == cleaned


def test_mkdir__converts_to_path_obj(tmpdir):
    """
    We want to make sure we convert our stings into path objects while
    also making sure the directory gets made.

    We've had some problems where the caller assumes `mkdir` takes `path` by
    reference, when infact it's by value - especially if its a string.

    this is essentially a sanity test to avoid any weird regressions.
    """
    str_path = f"{tmpdir.mkdir('assets')}/random/path"
    path = mkdir(str_path)

    assert isinstance(str_path, str)
    assert isinstance(path, pathlib.PosixPath)

    assert path.exists()
    assert str(path) == str_path


@pytest.mark.parametrize("path,expected", [
    ("anders-jilden.jpg", (1600, 2400)),
    ("avatar-blue.png", (901, 529)),
    ("earth.gif", (400, 400)),
    ("giphy.webp", (270, 480)),
])
def test_get_image_dimension(path, expected):
    t_img = utils.to_filestorage((shared_data.ASSET_DIR / path), path)
    assert image_proc.image_dimensions(t_img) == expected


def test_get_video_dimension():
    t_vid = utils.to_filestorage(
        (shared_data.ASSET_DIR / "big-bunny.mp4"), "big-bunny.mp4")

    assert image_proc.video_dimensions(t_vid) == (1080, 1920)


@pytest.mark.parametrize("height,width,expected", [
    (1080, 1920, "16/9"),
    (901, 529, "529/901"),
    (1600, 2400, "3/2"),
    (400, 400, "1/1"),
    (270, 480, "16/9"),
])
def test_get_aspect_ratio(height, width, expected):
    assert image_proc.aspect_ratio(height, width) == expected


# -- vault tests --

@pytest.fixture
def mock_vault_data():
    return {
        "vault": {
            "database": {
                "password": "super-secret",
            },
            "service": {
                "token": "abc123",
            },
        }
    }


def test_vault_item(mocker, mock_vault_data):
    mocker.patch(
        "corna.utils.vault_manager.get_decrypted_data",
        return_value=mock_vault_data,
    )
    
    assert vault_item("database.password") == "super-secret"


@pytest.mark.parametrize(
    "key",
    [
        "",
        "   ",
        ".database",
        "database.",
        "database..password",
    ],
)
def test_vault_item_rejects_invalid_key(mocker, key, mock_vault_data):
    mocker.patch(
        "corna.utils.vault_manager.get_decrypted_data",
        return_value=mock_vault_data,
    )

    with pytest.raises(VaultError):
        vault_item(key)


@pytest.mark.parametrize(
    "key",
    [
        "missing",
        "missing.password",
        "database.missing",
    ],
)
def test_vault_item_rejects_missing_key(mocker, key, mock_vault_data):
    mocker.patch(
        "corna.utils.vault_manager.get_decrypted_data",
        return_value=mock_vault_data,
    )

    with pytest.raises(VaultError, match=repr(key)):
        vault_item(key)


def test_get_item_rejects_traversal_below_value(mocker, mock_vault_data):
    mocker.patch(
        "corna.utils.vault_manager.get_decrypted_data",
        return_value=mock_vault_data,
    )

    with pytest.raises(VaultError):
        vault_item("database.password.foo")
