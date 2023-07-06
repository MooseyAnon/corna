import pytest


def test_dummy(client):

    res = client.get("/api/v1/dummy")
    actual = res.json
    assert actual == {"resp": "hello world"}
