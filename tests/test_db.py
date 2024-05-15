from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError

from corna.db import models


FROZEN_TIME = "2023-04-29T03:21:34"


def test_corna_simple_db_test(session):

    session.add(models.TestTable(id=1, description="test1"))
    session.commit()
    result = (
        session.query(models.TestTable)
        .filter(models.TestTable.description == "test1")
        .one()
    )

    assert result.id == 1
    assert result.description == "test1"


def test_image_nullable_fk(session):
    
    session.add(
        models.Media(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            url_extension="fake-extension",
            path="some/fake/path",
            created=FROZEN_TIME,
            size=8096,
            orphaned=False,
        )
    )

    session.commit()

    # check everything was saved correctly
    image = session.query(models.Media).first()

    assert image is not None
    assert image.uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert image.url_extension == "fake-extension"
    assert image.path == "some/fake/path"
    assert image.created.isoformat() == FROZEN_TIME
    assert image.size == 8096
    assert image.orphaned == False
    assert image.post_uuid is None
    assert image.post is None


def test_post_with_multiple_images(session, corna):

    corna = session.query(models.CornaTable).first()
    assert corna is not None

    session.add(
        models.PostTable(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            url_extension="fake-extension",
            created=FROZEN_TIME,
            type="picture",
            deleted=False,
            corna_uuid=corna.uuid,
            user_uuid=corna.user.uuid,
        )
    )

    image_deets = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    ]

    for index, uuid in enumerate(image_deets):

        session.add(
            models.Media(
                uuid=uuid,
                url_extension=f"fake-extension-{index}",
                path="some/fake/path",
                created=FROZEN_TIME,
                size=8096,
                post_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                orphaned=False,
            )
        )


    session.commit()

    post = session.query(models.PostTable).first()
    assert post is not None
    assert len(post.media) == 3

    for index, uuid in enumerate(image_deets):
        image = session.query(models.Media).get(uuid)

        assert image is not None
        assert image.uuid == uuid
        assert image.url_extension == f"fake-extension-{index}"
        assert image.path == "some/fake/path"
        assert image.created.isoformat() == FROZEN_TIME
        assert image.size == 8096
        assert image.post_uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert image.post is not None


def test_text_nullable_fk(session):

    content = (
        "There are three things I cannot tolerate: cowardice, "
        "bad haircuts, and military insurrection, and it is very "
        "unfortunate that our friend Vegeta possesses all three "
        "of these."
    )

    session.add(
        models.TextContent(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            title="Freeza was right.",
            created=FROZEN_TIME,
            content=content,
            )
    )

    session.commit()

    # check everything was saved correctly
    text = session.query(models.TextContent).first()

    assert text is not None
    assert text.uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert text.title == "Freeza was right."
    assert text.content == content
    assert text.created.isoformat() == FROZEN_TIME
    assert text.post_uuid is None
    assert text.post is None


def test_text_to_post_one_to_one(session, corna):

    content = (
        "There are three things I cannot tolerate: cowardice, "
        "bad haircuts, and military insurrection, and it is very "
        "unfortunate that our friend Vegeta possesses all three "
        "of these."
    )

    corna = session.query(models.CornaTable).first()
    assert corna is not None

    session.add(
        models.PostTable(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            url_extension="fake-extension",
            created=FROZEN_TIME,
            type="text",
            deleted=False,
            corna_uuid=corna.uuid,
            user_uuid=corna.user.uuid,
        )
    )

    session.add(
        models.TextContent(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            title="Freeza was right.",
            created=FROZEN_TIME,
            content=content,
            post_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
    )

    session.commit()

    post = session.query(models.PostTable).first()
    assert post is not None
    assert post.text is not None

    text = session.query(models.TextContent).first()
    assert text is not None

    assert text.uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert text.title == "Freeza was right."
    assert text.content == content
    assert text.created.isoformat() == FROZEN_TIME
    assert text.post_uuid == post.uuid
    assert text.post is not None


def test_post_with_multiple_text_not_allowed(session, corna):

    content = (
        "There are three things I cannot tolerate: cowardice, "
        "bad haircuts, and military insurrection, and it is very "
        "unfortunate that our friend Vegeta possesses all three "
        "of these."
    )

    corna = session.query(models.CornaTable).first()
    assert corna is not None

    session.add(
        models.PostTable(
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            url_extension="fake-extension",
            created=FROZEN_TIME,
            type="text",
            deleted=False,
            corna_uuid=corna.uuid
        )
    )

    text_deets = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    ]

    for uuid in text_deets:
        session.add(
            models.TextContent(
                uuid=uuid,
                title="Freeza was right.",
                created=FROZEN_TIME,
                content=content,
                post_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                )
        )

    # this should raise an IntegrityError as multiple text posts
    # are pointing to the same post element
    try:
        session.commit()
        assert False
    except IntegrityError:
        assert True
