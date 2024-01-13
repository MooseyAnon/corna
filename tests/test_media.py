"""Tests for media endpoints."""

import os

import pytest

from corna.db import models
from corna.controls import media_control
from corna.utils import image_proc
from tests import shared_data

@pytest.fixture(autouse=True)
def _all_media_based_stubs(tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for post
    related testing.
    """
    mocker.patch(
        "corna.utils.utils.random_short_string",
        return_value="abcdef",
    )
    mocker.patch(
        "corna.utils.image_proc.hash_image",
        return_value="thisisafakehash12345",
    )
    monkeypatch.setattr(
        image_proc,
        "PICTURE_DIR",
        tmpdir.mkdir("assets"),
    )


def test_upload(session, client, mocker):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post("/api/v1/media/upload", data={ "image": image })
    assert resp.status_code == 201

    expected = {
        "filename": f"{shared_data.ASSET_DIR}/anders-jilden.jpg",
        "size": os.stat((shared_data.ASSET_DIR / "anders-jilden.jpg")).st_size,
        "id": "00000000-0000-0000-0000-000000000000",
        "url_extension": "abcdef",
        "mime_type": "image/jpeg"
    }

    assert resp.json == expected

    # ensure file is actually saved
    expected_path = image_proc.PICTURE_DIR / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    # make sure db is ok
    assert session.query(models.Images).count() == 1
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    image = session.query(models.Images).first()
    assert image is not None

    assert image.orphaned == True


def test_file_not_saved_properly(session, client, mocker):
    mocker.patch(
        "corna.utils.image_proc.save",
        side_effect=OSError("Failure")
    )

    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post("/api/v1/media/upload", data={ "image": image })
    assert resp.status_code == 500
    assert resp.json["message"] == "Unable to save file"

    # ensure nothing is saved
    assert session.query(models.Images).count() == 0


def test_download(session, client):
    # add image
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post("/api/v1/media/upload", data={ "image": image })
    assert resp.status_code == 201

    # we dont want to call the main download endpoint as it sends a file
    # so we'll call the download function in media_control directly and 
    # ensure we get the proper path
    from werkzeug.utils import secure_filename
    url_extension = resp.json["url_extension"]
    expected_filename = secure_filename(resp.json["filename"])
    expected_path = (
        image_proc.PICTURE_DIR 
        / "thi/sis/afa/kehash12345" 
        / expected_filename
    )
    assert media_control.download(session, url_extension) == expected_path


def test_download_fail(client):

    resp = client.get("/api/v1/media/download/fake-url")
    assert resp.status_code == 400
    assert resp.json["message"] == "File not found"
