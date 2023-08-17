import json
import os

from freezegun import freeze_time
import pytest
import requests
import werkzeug

from corna.controls import post_control
from corna.db import models
from corna.utils import utils
from tests import shared_data


FROZEN_TIME = "2023-04-29T03:21:34"


def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f'{num:.1f} {x}'
        num /= 1024.0


@pytest.fixture(autouse=True)
def _all_post_based_stubs(tmpdir, mocker, monkeypatch):
    """Environment variable and function mocks needed for post
    related testing.
    """
    mocker.patch(
        "corna.controls.post_control.random_short_string",
        return_value="abcdef",
    )
    mocker.patch(
        "corna.utils.image_proc.hash_image",
        return_value="thisisafakehash12345",
    )
    monkeypatch.setattr(
        post_control,
        "PICTURE_DIR",
        tmpdir.mkdir("assets"),
    )


@freeze_time(FROZEN_TIME)
def test_create_post(session, client, blog):
    resp = client.post(
        f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
        data=shared_data.simple_text_post
    )
    assert resp.status_code == 201

    # check database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    blog = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.blog_info["domain_name"]
        )
        .one()
    )
    assert len(blog.posts) == 1

    post = session.query(models.PostTable).first()
    text = session.query(models.TextPost).first()
    
    # checking foreign key relationships
    assert post.blog_uuid == blog.blog_uuid
    assert post.mapper is text.mapper
    assert post.mapper.text_post_uuid == text.uuid

    assert post.type == shared_data.simple_text_post["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME

    assert text.body == shared_data.simple_text_post["content"]
    assert text.title == shared_data.simple_text_post["title"]

    # make sure the save was mutually exclusive in the mapper object
    mapper = post.mapper

    assert mapper.post_uuid == post.post_uuid
    assert mapper.photo_post_uuid is None
    assert mapper.photo is None


@freeze_time(FROZEN_TIME)
def test_post_with_picture(session, client, blog):
    assets = post_control.PICTURE_DIR
    
    resp = client.post(
        f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
        data=shared_data.post_with_picture
    )

    expected_path = assets / "thi/sis/afa/kehash12345"
    assert expected_path.exists()
    assert len(expected_path.listdir()) == 1
    for file in expected_path.listdir():
        # assert we've saved some data successfully
        assert os.stat(file).st_size >= 1024

    # ensure database relationships are correct
    posts = session.query(models.PostTable).all()
    assert len(posts) == 1

    blog = (
        session
        .query(models.CornaTable)
        .filter(
            models.CornaTable.domain_name
            == shared_data.blog_info["domain_name"]
        )
        .one()
    )
    assert len(blog.posts) == 1
    post = session.query(models.PostTable).first()
    pic = session.query(models.PhotoPost).first()

    # checking foreign key relationships
    assert post.blog_uuid == blog.blog_uuid
    assert post.mapper is pic.mapper
    assert post.mapper.photo_post_uuid == pic.uuid

    assert post.type == shared_data.post_with_picture["type"]
    assert post.deleted == False
    assert post.created.isoformat() == FROZEN_TIME
    assert pic.caption == shared_data.post_with_picture["caption"]
    assert pic.size > 1024
    assert pic.path == expected_path.listdir()[0]

    # make sure the save was mutually exclusive in the mapper object
    mapper = post.mapper

    assert mapper.post_uuid == post.post_uuid
    assert mapper.text_post_uuid is None
    assert mapper.text is None


@freeze_time(FROZEN_TIME)
def test_get_one_post(session, client, blog):
    assets = post_control.PICTURE_DIR

    resp = client.post(
        f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
        data=shared_data.simple_text_post
    )
    assert resp.status_code == 201

    resp = client.get(f"api/v1/posts/{shared_data.blog_info['domain_name']}")
    
    # there should only be 4 fields in the response. This test
    # is to make sure marshmallow is dropping fields correctly
    assert len(resp.json["posts"][0]) == 4

    post = resp.json["posts"][0]
    assert post["body"] == shared_data.simple_text_post["content"]
    assert post["title"] == shared_data.simple_text_post["title"]
    assert post["created"] == FROZEN_TIME
    assert post["type"] == "text"


@freeze_time(FROZEN_TIME)
def test_get_multiple_posts(session, client, blog):
    assets = post_control.PICTURE_DIR

    # opening the picture file in a shared directory fucks things up
    # over multiple runs, so its easier just to put it in here
    post_with_picture = {
        "type": "picture",
        "caption": "this is a picture I did not take",
        "pictures": (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb"),
    }

    for post in (shared_data.simple_text_post, post_with_picture):
        resp = client.post(
            f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
            data=post
        )
        assert resp.status_code == 201

    resp = client.get(f"api/v1/posts/{shared_data.blog_info['domain_name']}")
    posts = resp.json["posts"]

    for post in posts:
        if post["type"] == "text":
            assert post["body"] == shared_data.simple_text_post["content"]
            assert post["title"] == shared_data.simple_text_post["title"]
            assert post["created"] == FROZEN_TIME
        if post["type"] == "picture":
            assert post["caption"] == shared_data.post_with_picture["caption"]
            assert post["url"] is not None
            assert post["created"] == FROZEN_TIME


@freeze_time(FROZEN_TIME)
def test_get_image(session, client, blog):
    assets = post_control.PICTURE_DIR

    # opening the picture file in a shared directory fucks things up
    # over multiple runs, so its easier just to put it in here
    post_with_picture = {
        "type": "picture",
        "caption": "this is a picture I did not take",
        "pictures": (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb"),
    }

    resp = client.post(
        f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
        data=post_with_picture
    )
    assert resp.status_code == 201

    expected_path = assets / "thi/sis/afa/kehash12345"
    assert expected_path.exists()

    full_path = expected_path.listdir()[0]
    assert post_control.get_image(
        session,
        shared_data.blog_info['domain_name'],
        "abcdef") == full_path


def test_path_collision(session, client, capsys, blog):
    assets = post_control.PICTURE_DIR

    # opening the picture file in a shared directory fucks things up
    # over multiple runs, so its easier just to put it in here
    post_with_picture = {
        "type": "picture",
        "caption": "this is a picture I did not take",
        "pictures": (shared_data.ASSET_DIR / "anders-jilden.jpg").open("rb"),
    }

    resp = client.post(
        f"/api/v1/posts/{shared_data.blog_info['domain_name']}",
        data=post_with_picture
    )
    assert resp.status_code == 201
    # check pic exists
    assert len((assets / "thi/sis/afa/kehash12345").listdir()) == 1

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
    file = FileStorage(filename=str(assets / "same-pic-different-name.jpg"))
    post_control.handle_pictures(file)

    captured = capsys.readouterr()
    assert "Photo directory exists, duplicate?" in captured.err

    assert len((assets / "thi/sis/afa/kehash12345").listdir()) == 2
