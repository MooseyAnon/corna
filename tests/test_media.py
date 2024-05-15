"""Tests for media endpoints."""

import os

import pytest

from corna.db import models
from corna.controls import media_control
from corna.utils import image_proc
from tests import shared_data

@pytest.fixture(autouse=True)
def _all_media_based_stubs(request, tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for post
    related testing.
    """
    if not ("nostubs" in request.keywords):
        mocker.patch(
            "corna.utils.image_proc.hash_image",
            return_value="thisisafakehash12345",
        )
    mocker.patch(
        "corna.utils.utils.random_short_string",
        return_value="abcdef",
    )
    mocker.patch(
        "corna.utils.image_proc.random_hash",
        return_value="thisisafakestringhash",
    )
    monkeypatch.setattr(
        image_proc,
        "PICTURE_DIR",
        tmpdir.mkdir("assets"),
    )


def test_upload(session, client, mocker, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    type_ = "image"
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
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
    expected_path = image_proc.PICTURE_DIR / type_ / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    # make sure db is ok
    assert session.query(models.Media).count() == 1
    assert session.query(models.Images).count() == 1
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    media = session.query(models.Media).first()
    image = session.query(models.Images).first()
    assert media is not None
    assert image is not None

    assert media.orphaned == True
    assert media.image_uuid == image.uuid
    assert media.type == type_

    assert image.hash == "thisisafakehash12345"


def test_file_not_saved_properly(session, client, mocker, login):
    mocker.patch(
        "corna.utils.image_proc.save",
        side_effect=OSError("Failure")
    )

    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": "image"},
    )
    assert resp.status_code == 500
    assert resp.json["message"] == "Unable to save file"

    # ensure nothing is saved
    assert session.query(models.Images).count() == 0
    assert session.query(models.Media).count() == 0


def test_download(session, client, login):
    # add image
    type_ = "image"
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    # we dont want to call the main download endpoint as it sends a file
    # so we'll call the download function in media_control directly and 
    # ensure we get the proper path
    from werkzeug.utils import secure_filename
    url_extension = resp.json["url_extension"]
    expected_filename = secure_filename(resp.json["filename"])
    expected_path = (
        image_proc.PICTURE_DIR 
        / type_
        / "thi/sis/afa/kehash12345" 
        / expected_filename
    )
    assert media_control.download(session, url_extension) == expected_path


def test_download_fail(client):

    resp = client.get("/api/v1/media/download/fake-url")
    assert resp.status_code == 400
    assert resp.json["message"] == "File not found"


def test_upload_video(session, client, mocker, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    type_ = "video"
    image = (shared_data.ASSET_DIR / "big-bunny.mp4").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    expected = {
        "filename": f"{shared_data.ASSET_DIR}/big-bunny.mp4",
        "size": os.stat((shared_data.ASSET_DIR / "big-bunny.mp4")).st_size,
        "id": "00000000-0000-0000-0000-000000000000",
        "url_extension": "abcdef",
        "mime_type": "video/mp4"
    }

    assert resp.json == expected

    # ensure file is actually saved
    expected_path = image_proc.PICTURE_DIR / type_ / "thi/sis/afa/kestringhash"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    # make sure db is ok
    assert session.query(models.Media).count() == 1
    # ensure no images were created
    assert session.query(models.Images).count() == 0
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    media = session.query(models.Media).first()
    assert media is not None
    assert media.type == type_
    assert media.image_uuid is None

    assert media.orphaned == True


def test_download_video(session, client, login):
    type_ = "video"
    image = (shared_data.ASSET_DIR / "big-bunny.mp4").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    # we dont want to call the main download endpoint as it sends a file
    # so we'll call the download function in media_control directly and 
    # ensure we get the proper path
    from werkzeug.utils import secure_filename
    url_extension = resp.json["url_extension"]
    expected_filename = secure_filename(resp.json["filename"])
    expected_path = (
        image_proc.PICTURE_DIR 
        / type_
        / "thi/sis/afa/kestringhash" 
        / expected_filename
    )
    assert media_control.download(session, url_extension) == expected_path


def test_upload_gif(session, client, mocker, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    type_ = "gif"
    image = (shared_data.ASSET_DIR / "giphy.webp").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    expected = {
        "filename": f"{shared_data.ASSET_DIR}/giphy.webp",
        "size": os.stat((shared_data.ASSET_DIR / "giphy.webp")).st_size,
        "id": "00000000-0000-0000-0000-000000000000",
        "url_extension": "abcdef",
        "mime_type": "image/webp"
    }

    assert resp.json == expected

    # ensure file is actually saved
    expected_path = image_proc.PICTURE_DIR / type_ / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    # make sure db is ok
    assert session.query(models.Media).count() == 1
    # ensure no images were created
    assert session.query(models.Images).count() == 1
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    media = session.query(models.Media).first()
    assert media is not None
    assert media.type == type_
    assert media.image_uuid is not None

    assert media.orphaned == True


@pytest.mark.nostubs
def test_path_collision(session, client, capsys, mocker, login):
    # test image already exists
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    assets = image_proc.PICTURE_DIR

    type_ = "image"
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    # ensure file is actually saved
    assert session.query(models.Media).count() == 1
    path = session.query(models.Media).first().path
    expected_path = (image_proc.PICTURE_DIR / path).parts()[-2]
    assert len(expected_path.listdir()) == 1

    # write picture to tmpdir to use again
    import shutil
    shutil.copy(
        (shared_data.ASSET_DIR / "anders-jilden.jpg"),
        (assets / "same-pic-different-name.jpg")
    )

    assert (assets / "same-pic-different-name.jpg").exists()
    # putting it into the same file should raise a FileExistsError
    # but should still be saved
    from werkzeug.datastructures import FileStorage
    file = FileStorage(
        stream=(assets / "same-pic-different-name.jpg").open("rb"),
        filename="same-pic-different-name.jpg"
    )
    image_hash = image_proc.hash_image(file)
    image_proc.save(file, bucket="image", hash_=image_hash)

    captured = capsys.readouterr()
    assert "Photo directory exists, duplicate?" in captured.err

    assert len(expected_path.listdir()) == 2



def test_nothing_saved_in_database_if_image_save_fails(
    session,
    client,
    mocker,
    login,
):
    mocker.patch("corna.utils.image_proc.save", side_effect=OSError("error!"))
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    type_ = "image"
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )

    assert resp.status_code == 500
    assert resp.json["message"] == "Unable to save file"

    assert session.query(models.Media).count() == 0
    assert session.query(models.Images).count() == 0


@pytest.mark.nostubs
def test_hash_gif():
    name = "giphy.webp"
    file = (shared_data.ASSET_DIR / name) 
    assert file.exists()

    from werkzeug.datastructures import FileStorage
    file = FileStorage(stream=file.open("rb"), filename=name)
    image_hash = image_proc.hash_image(file)
    # this hash is returned when MD5 receives 0 data as input
    # i.e. the MD5sum of "nothing"
    # more info: https://stackoverflow.com/q/10909976
    empty_hash = "d41d8cd98f00b204e9800998ecf8427e"
    assert image_hash != empty_hash
