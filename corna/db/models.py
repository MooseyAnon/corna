"""Models for the Corna app."""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
    String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import DetachedInstanceError
from werkzeug.security import check_password_hash, generate_password_hash


class Base:
    """Declarative base class for SQLAlchemy models."""
    # This cannot be labelled as @classmethod as SQLAlchemy will fail to find
    # primary keys. But it is a class method so suppress Pylint errors.
    @declared_attr
    def __tablename__(cls):  # pylint: disable=no-self-argument
        return cls.__name__.lower()  # pylint: disable=no-member

    def __repr__(self):
        args = []
        for column in inspect(self).attrs:
            try:
                val = getattr(self, column.key)
            except DetachedInstanceError:
                val = "<table-not-joined>"

            if hasattr(val, '__iter__') and not isinstance(val, str):
                args.append(f"{column.key}=[{len(val)} items]")
            elif isinstance(val, Base):
                args.append(
                    f"{column.key}={val.__class__.__name__}(pk="
                    f"{inspect(val).identity})")
            else:
                args.append(f"{column.key}={val!r}")
        return f"{self.__class__.__name__}({', '.join(args)})"


Base = declarative_base(cls=Base)


class TestTable(Base):
    """Just a test table."""

    __test__ = False  # Suppress pytest warning

    id = Column(Integer, primary_key=True)
    description = Column(Text, doc="Test description")


class UserTable(Base):
    """User table."""

    __tablename__ = "users"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    username = Column(
        Text,
        unique=True,
        index=True,
        doc="user handle",
    )
    email_address = Column(
        Text,
        ForeignKey("emails.email_address"),
        unique=True,
    )
    date_created = Column(
        DateTime,
        doc="date of account creation",
    )
    email = relationship(
        "EmailTable",
        back_populates="user",
    )
    corna = relationship(
        "CornaTable",
        back_populates="user",
    )


class EmailTable(Base):
    """Table to hold email address

    This is for GDPR laws
    """
    __tablename__ = "emails"

    email_address = Column(
        Text,
        primary_key=True,
    )
    password_hash = Column(
        String(128),
        doc="hash of password",
    )
    user = relationship("UserTable", uselist=False, back_populates="email")

    @property
    def password(self) -> None:
        """Getter method for a user passsword.

        Nothing should attempt to read the password, in such a
        case we raise a value error.

        :raises ValueError: case of illegal password read attempt
        """
        raise ValueError("Password is not viewable")

    @password.setter
    def password(self, password: str) -> None:
        """Setter method for a user password.

        :param str password: users password to be hashed
        """
        self.password_hash = generate_password_hash(password)

    def is_password(self, password: str) -> bool:
        """Check if user password is correct.
        :param str password: the password to check against
        :returns: true or false
        :rtype: bool
        """
        return check_password_hash(self.password_hash, password)


class SessionTable(Base):
    """Session data for when a user logs in.

    This is largely and ephemeral data. The whole row
    gets deleted after a user session ends.

    This table will currently have the session cookies
    as well but this is only temporary.
    Cookies will be saved/cached in a redis table.

    --actually this whole table can be moved to redis
    -- is it worth makeing the cookie_id PK?
    """
    __tablename__ = "sessions"

    session_id = Column(
        Text,
        primary_key=True,
    )
    cookie_id = Column(
        Text,
        unique=True,
        nullable=False,
        index=True,
    )
    user_uuid = Column(
        UUID,
        ForeignKey("users.uuid"),
        unique=True,
    )
    user = relationship(
        "UserTable"
    )


class CornaTable(Base):
    """Corna table."""
    __tablename__ = "corna"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    domain_name = Column(
        Text,
        unique=True,
        index=True,
        doc="chosen domain name for Corna"
    )
    title = Column(
        Text,
        doc="title of the Corna",
    )
    date_created = Column(
        DateTime,
        doc="creation date of Corna",
    )
    user_uuid = Column(
        UUID,
        ForeignKey("users.uuid"),
        unique=True,
    )
    user = relationship(
        "UserTable",
        back_populates="corna",
    )
    posts = relationship(
        "PostTable",
        back_populates="corna"
    )
    about = Column(
        UUID,
        nullable=True,
        doc="Corna about/bio",
    )
    theme = Column(
        UUID,
        nullable=True,
        doc="Theme for Corna",
    )

    ForeignKeyConstraint(
        ["about"],
        ["text.uuid"],
        use_alter=True,
        ondelete="SET NULL",
    )

    ForeignKeyConstraint(
        ["theme"],
        ["theme.uuid"],
        use_alter=True,
        ondelete="SET NULL",
    )


class PostTable(Base):
    """"Post Table."""

    __tablename__ = "posts"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    url_extension = Column(
        Text,
        index=True,
        unique=True,
        doc="The url extension of the post",
    )
    created = Column(
        DateTime,
        doc="post creation timestamp",
    )
    type = Column(
        Text,
        doc="type of post",
    )
    deleted = Column(
        Boolean,
        doc="post has been deleted, do not show",
    )
    corna_uuid = Column(
        UUID,
        ForeignKey("corna.uuid"),
    )
    corna = relationship(
        "CornaTable",
        back_populates="posts",
    )
    text = relationship(
        "TextContent",
        uselist=False,
        back_populates="post",
    )
    images = relationship(
        "Images",
        back_populates="post",
    )


class TextContent(Base):
    """Table for holding text and related data."""

    __tablename__ = "text"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    title = Column(
        Text,
        doc="Title of the text"
    )
    content = Column(
        Text,
        doc="Any text content associated with the post.",
    )
    inner_html = Column(
        Text,
        doc="HTML representation of the content, this will come from browsers "
            "so not all posts will have this."
    )
    created = Column(
        DateTime,
        doc="Text creation timestamp",
    )
    post_uuid = Column(
        UUID,
        ForeignKey("posts.uuid"),
        unique=True,
        nullable=True,
        doc="A nullable FK to the posts table. The reason we allow this field "
            "to be nullable is because this means the text table can be a "
            "bit more generic e.g. we can use it to save the 'about' section "
            "for a corna which will not be associated with any post.",
    )
    post = relationship(
        "PostTable",
        back_populates="text",
    )


class Images(Base):
    """Table for image data."""

    __tablename__ = "images"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    url_extension = Column(
        Text,
        index=True,
        unique=True,
        doc="The url extension of the picture, this will be used to "
            "fetch the image on the client.",
    )
    path = Column(
        Text,
        doc="path to image",
    )
    size = Column(
        Integer,
        doc="Size of file in bytes. This is essentially output of `stat`",
    )
    created = Column(
        DateTime,
        doc="image creation timestamp",
    )
    orphaned = Column(
        Boolean,
        nullable=False,
        doc="Describes if the image is 'loose'. Essentially a boolean values "
            "which will be used to clean up the database/image storage. There "
            "are situations where we may upload an image but its not used "
            "e.g. for image preview on the client but the user subsequently "
            "deletes the image before creating the post."
    )
    post_uuid = Column(
        UUID,
        ForeignKey("posts.uuid"),
        nullable=True,
        doc="A nullable FK to the posts table. The reason we allow this field "
            "to be nullable is because this means the images table can be a "
            "bit more generic e.g. we can use it to save a favicon which will "
            "not be associated with any post.",
    )
    post = relationship(
        "PostTable",
        back_populates="images",
    )


class Themes(Base):
    """Table for managing corna themes."""

    __tablename__ = "themes"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    name = Column(
        Text,
        doc="The name of the theme",
    )
    description = Column(
        Text,
        doc="Short, optional, description of the theme",
    )
    created = Column(
        DateTime,
        doc="Date theme was created",
    )
    path = Column(
        Text,
        doc="Path to the main index.html of the theme, relative to themes "
            "directory.",
    )
    status = Column(
        Text,
        nullable=False,
        doc="The current status of the PR i.e. do we know the full "
            "path to the theme yet? This is needed because there may "
            "be a delay between the initial time that the theme gets "
            "submitted and the time we know the full path to the theme",
    )
    creator_user_id = Column(
        UUID,
        ForeignKey("users.uuid"),
        doc="User who created the theme, for attribution",
    )
    thumbnail = Column(
        UUID,
        ForeignKey("images.uuid"),
        nullable=True,
        doc="Thumbnail of the theme to display to users when selecting",
    )
