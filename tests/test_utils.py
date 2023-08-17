import pytest

from corna.utils import encodings, secure


def test_signing_similar_messages():

    m1 = "aaaaaaaaa"
    m2 = "aaaaaaaab"

    s1 = secure.sign(m1)
    s2 = secure.sign(m2)

    _, s1_sig = secure.unsign(s1)
    _, s2_sig = secure.unsign(s2)

    assert secure.verify(m1, s1_sig)
    assert secure.verify(m2, s2_sig)

    assert not secure.verify(m1, s2_sig)
    assert not secure.verify(m2, s1_sig)


def test_unsign():

    sig = secure.sign("aaaaaaaaa")
    orig_message, _ = secure.unsign(sig)
    assert orig_message == b"aaaaaaaaa"


def test_fake_message():
    message = "I am a fake message"
    assert secure.verify(message, encodings.base64_encode(message)) == False
