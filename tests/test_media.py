"""Tests for media endpoints."""

import json
import os
import sys

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

    monkeypatch.setattr(
        image_proc,
        "CHUNK_DIR",
        tmpdir.mkdir("assets/chunks"),
    )


def _metadata(received=[], total_chunks=3):
    """Mock metadata."""
    return {
        "received": received,
        "totalChunks": total_chunks,
    }


def _chunk_file(file_path, chunk_size=100 * 1024):
    """Split a file into chunks.

    :param file_path: Path to the file to be chunked.
    :param chunk_size: Size of each chunk in bytes. Default is 100KB (100 * 1024).
    :yield: A chunk of the file.
    """
    from io import BytesIO

    with open(file_path, 'rb') as file:
        while chunk := file.read(chunk_size):
            yield BytesIO(chunk)


def _ceiling_division(n, d):
    """Return the ceiling of integer division.

    Stolen from here: https://stackoverflow.com/a/17511341
    """
    return -(n // -d)


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
    assert image.height == 1600
    assert image.width == 2400


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
    # this returns a db column
    media_obj = media_control.download(session, url_extension)
    assert media_control.to_path(media_obj) == expected_path


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
    # ensure video has been saved
    assert session.query(models.Videos).count() == 1
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    media = session.query(models.Media).first()
    video = session.query(models.Videos).first()
    assert media is not None
    assert media.type == type_
    assert media.image_uuid is None

    assert media.orphaned == True

    assert video.hash == "thisisafakestringhash"
    assert video.height == 1080
    assert video.width == 1920


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
    media_obj = media_control.download(session, url_extension)
    assert media_control.to_path(media_obj) == expected_path


def test_upload_gif_with_dot_gif_extension(session, client, mocker, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    type_ = "gif"
    image = (shared_data.ASSET_DIR / "earth.gif").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    expected = {
        "filename": f"{shared_data.ASSET_DIR}/earth.gif",
        "size": os.stat((shared_data.ASSET_DIR / "earth.gif")).st_size,
        "id": "00000000-0000-0000-0000-000000000000",
        "url_extension": "abcdef",
        "mime_type": "image/gif"
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


@pytest.mark.skipif(sys.version_info < (3, 11), reason="requires python3.11 or higher")
def test_upload_image_with_webp_format(client, mocker, login):
    """Flask uses werkzeug's FileStorage wrapper on all file objects uploaded
    via a form i.e. multipart/form-data. According to werkzeug's source code
    the FileStorage wrapper tries to figure out the mimetype of the in coming
    file object, however if the mimetype is not determined by theFileStorage
    object, it falls back on a module called mimetype which is part of cpythons
    stdlib.

    It seems that support for recognising the webp format was not added to the
    mimetype module until python3.11[1], thus this test will not pass until we
    update.

    Currently, this is essentially a placeholder for a test we would like to
    run but is currently breaking our tests.

    [1] https://github.com/python/cpython/pull/29259#pullrequestreview-960709458
    """
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    filename = shared_data.ASSET_DIR / "giphy.webp"
    type_ = "gif"
    image = filename.open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": type_},
    )
    assert resp.status_code == 201

    expected = {
        "filename": f"{filename}",
        "size": os.stat(filename).st_size,
        "id": "00000000-0000-0000-0000-000000000000",
        "url_extension": "abcdef",
        # this line fails as webp is not a recognised format until python3.11
        "mime_type": "image/webp"
    }

    assert resp.json == expected


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


@pytest.mark.nostubs
def test_random_avatar_gen(client, session, login):
    # upload avatars and one extra image to make sure it does not
    # get selected
    image = (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb")
    resp = client.post(
        "/api/v1/media/upload",
        data={"image": image, "type": "image"},
    )
    assert resp.status_code == 201
    reg_slug = resp.json["url_extension"]

    # upload avatars
    av_slugs = set()
    for avatar in ("blue", "coral", "green", "pink", "purple", "yellow"):
        image = (shared_data.ASSET_DIR / f"avatar-{avatar}.png").open("rb")
        resp = client.post(
            "/api/v1/media/upload",
            data={"image": image, "type": "avatar"},
        )
        assert resp.status_code == 201

        av_slugs.add(resp.json["url_extension"])

    assert session.query(models.Media).count() == 7
    assert session.query(models.Images).count() == 7

    # ---------------------- test starts --------------------------

    resp = client.get("/api/v1/media/avatar")
    assert resp.status_code == 200

    fin_slug = resp.json["slug"]
    assert fin_slug != reg_slug
    assert fin_slug in av_slugs


def test_chunk_status__no_chunks_uploaded(client):

    fake_upload_id = "000111111"
    base_path = image_proc.CHUNK_DIR.mkdir(fake_upload_id)

    meta_path = base_path / "meta.json"

    with open(meta_path, "w") as fd:
        fd.write(json.dumps(_metadata()))

    resp = client.get(f"/api/v1/media/chunk/status/{fake_upload_id}")
    assert resp.status_code == 200

    assert resp.json["complete"] == False
    assert resp.json["message"] == "3 chunks missing"


def test_chunk_status__upload_complete(client):

    fake_upload_id = "000111111"
    base_path = image_proc.CHUNK_DIR.mkdir(fake_upload_id)

    meta_path = base_path / "meta.json"

    with open(meta_path, "w") as fd:
        fd.write(json.dumps(_metadata(received=["00000", "11111"], total_chunks=2)))

    resp = client.get(f"/api/v1/media/chunk/status/{fake_upload_id}")
    assert resp.status_code == 200

    assert resp.json["complete"] == True
    assert resp.json["message"] == "upload complete"


def test_chunk_status__no_metadata_file(client):
    """
    No metadata file here means that either the upload_id is wrong or there
    has been no attempt to upload chunks using the corresponding id i.e. the
    upload_id does not exist.

    These two cases are essentially the same thing.
    """
    fake_upload_id = "000111111"

    resp = client.get(f"/api/v1/media/chunk/status/{fake_upload_id}")
    assert resp.status_code == 404

    assert resp.json["message"] == "No upload being processed"


def test_chunk_status__malformed_metadata_file(client):

    fake_upload_id = "000111111"
    base_path = image_proc.CHUNK_DIR.mkdir(fake_upload_id)

    meta_path = base_path / "meta.json"

    with open(meta_path, "w") as fd:
        fd.write(json.dumps({"random-key": "random-value"}))

    resp = client.get(f"/api/v1/media/chunk/status/{fake_upload_id}")
    assert resp.status_code == 500

    assert resp.json["message"] == "Error processing upload metadata"


def test_chunk_upload__full_upload(client, login):

    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    fake_upload_id = "0000011111"

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    for index, chunk in enumerate(_chunk_file(fp)):

        req["chunk"] = (chunk, 'application/octet-stream')
        req["chunkIndex"] = index

        resp = client.post("/api/v1/media/chunk/upload", data=req)
        assert resp.status_code == 201
        # ensure correct number of chunks are saved
        assert int(resp.json["received"]) == index + 1 
        assert resp.json["uploadId"] == fake_upload_id

        if index < (total_chunks - 1):
            assert resp.json["message"] == f"chunk {index} stored"

        # check when upload completed
        else:
            assert resp.json["message"] == "upload complete"

    # ensure main dirs/files are created
    assert (image_proc.CHUNK_DIR / fake_upload_id / "meta.json").exists()
    assert (image_proc.CHUNK_DIR / fake_upload_id / "parts").exists()

    received = None
    # read metadata file and check fields are legit
    with open((image_proc.CHUNK_DIR / fake_upload_id / "meta.json"), "r") as fd:
        m_data = json.load(fd)

        assert m_data["totalChunks"] == total_chunks
        assert len(m_data["received"]) == total_chunks

        received = set(m_data["received"])

    # loop through expected indexes and see if they all exist
    for i in range(total_chunks):
        assert (image_proc.CHUNK_DIR / fake_upload_id / "parts" / f"{i:06d}.part").exists()
        # check if its in received
        assert i in received


def test_chunk_upload__merge(mocker, client, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    # test setup
    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    fake_upload_id = "0000011111"

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    for index, chunk in enumerate(_chunk_file(fp)):

        req["chunk"] = (chunk, 'application/octet-stream')
        req["chunkIndex"] = index

        resp = client.post("/api/v1/media/chunk/upload", data=req)
        assert resp.status_code == 201
        # ensure correct number of chunks are saved
        assert int(resp.json["received"]) == index + 1 
        assert resp.json["uploadId"] == fake_upload_id

        if index < (total_chunks - 1):
            assert resp.json["message"] == f"chunk {index} stored"

        # check when upload completed
        else:
            assert resp.json["message"] == "upload complete"

    # ensure main dirs/files are created
    assert (image_proc.CHUNK_DIR / fake_upload_id / "meta.json").exists()
    assert (image_proc.CHUNK_DIR / fake_upload_id / "parts").exists()

    # --------- test starts here ---------
    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 201

    expected = {
        "id": "00000000-0000-0000-0000-000000000000",
        "filename": "big-bunny.mp4",
        "mime_type": "video/mp4",
        "size": file_size,
        "url_extension": "abcdef",
    }

    assert resp.json == expected


def test_chunk_upload__merge_ensure_cleanup(mocker, client, session, login):
    mocker.patch(
        "corna.utils.utils.get_uuid",
        return_value="00000000-0000-0000-0000-000000000000",
    )

    # test setup
    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    fake_upload_id = "0000011111"

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    for index, chunk in enumerate(_chunk_file(fp)):

        req["chunk"] = (chunk, 'application/octet-stream')
        req["chunkIndex"] = index

        resp = client.post("/api/v1/media/chunk/upload", data=req)
        assert resp.status_code == 201

    # ensure main dirs/files are created
    assert (image_proc.CHUNK_DIR / fake_upload_id / "meta.json").exists()
    assert (image_proc.CHUNK_DIR / fake_upload_id / "parts").exists()

    # --------- test starts here ---------
    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 201

    expected = {
        "id": "00000000-0000-0000-0000-000000000000",
        "filename": "big-bunny.mp4",
        "mime_type": "video/mp4",
        "size": file_size,
        "url_extension": "abcdef",
    }

    assert resp.json == expected

    # check cleanup
    assert not (image_proc.CHUNK_DIR / fake_upload_id).exists()

    # ensure file is actually saved
    expected_path = image_proc.PICTURE_DIR / "video/thi/sis/afa/kestringhash"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size == file_size

    # make sure db is ok
    assert session.query(models.Media).count() == 1
    # ensure no images were created
    assert session.query(models.Images).count() == 0
    # ensure no posts have been created
    assert session.query(models.PostTable).count() == 0

    media = session.query(models.Media).first()
    assert media is not None
    assert media.type == "video"
    assert media.image_uuid is None

    assert media.orphaned == True


def test_chunk_upload__merge_file_too_large(monkeypatch, client, login):
    monkeypatch.setattr(image_proc, "MAX_BLOB_SIZE", 100)

    # test setup
    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    fake_upload_id = "0000011111"

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    for index, chunk in enumerate(_chunk_file(fp)):

        req["chunk"] = (chunk, 'application/octet-stream')
        req["chunkIndex"] = index

        resp = client.post("/api/v1/media/chunk/upload", data=req)
        assert resp.status_code == 201

    # ----- test starts here -----
    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 500

    assert resp.json["message"] == "[Errno 27] File too large for processing"


def test_chunk_upload__merge_in_press(client, login):
    # create fake lock
    fake_upload_id = "000111111"
    base_path = image_proc.CHUNK_DIR.mkdir(fake_upload_id)

    meta_path = base_path / ".merge.lock"

    with open(meta_path, "w") as fd:
        fd.write(json.dumps({"random-key": "random-value"}))


    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    for index, chunk in enumerate(_chunk_file(fp)):

        req["chunk"] = (chunk, 'application/octet-stream')
        req["chunkIndex"] = index

        resp = client.post("/api/v1/media/chunk/upload", data=req)
        assert resp.status_code == 201

    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 400

    assert resp.json["message"] == "Merge in progress"


def test_chunk_upload__merge_has_upload_id(client, login):
    fake_upload_id = "000111111"
    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 500

    assert resp.json["message"] == f"No upload associcated with Id '{fake_upload_id}'"


def test_chunk_upload__merge_incomplete_upload(client, login):
     # test setup
    fp = (shared_data.ASSET_DIR / "big-bunny.mp4")
    chunk_size = 100 * 1024
    file_size = os.stat(fp).st_size
    total_chunks = _ceiling_division(file_size, chunk_size)

    fake_upload_id = "0000011111"

    req = {
        "totalChunks": total_chunks,
        "uploadId": fake_upload_id,
    }

    chunk = _chunk_file(fp)
    req["chunk"] = (next(chunk), 'application/octet-stream')
    req["chunkIndex"] = 0

    resp = client.post("/api/v1/media/chunk/upload", data=req)
    assert resp.status_code == 201

    # --- test starts here ----
    req = {
        "filename": "big-bunny.mp4",
        "uploadId": fake_upload_id,
        "contentType": "video",
    }

    resp = client.post("/api/v1/media/chunk/merge", json=req)
    assert resp.status_code == 500

    assert resp.json["message"] == f"Incomplete file, 10 chunks missing"
