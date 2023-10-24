"""Models for the Corna app."""

# pylint: disable=too-few-public-methods
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text)
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
        for column in inspect(self).attrs:  # pylint: disable=not-callable
            try:
                val = getattr(self, column.key)
            except DetachedInstanceError:
                val = "<table-not-joined>"

            if hasattr(val, '__iter__') and not isinstance(val, str):
                args.append(f"{column.key}=[{len(val)} items]")
            elif isinstance(val, Base):
                # pylint: disable=not-callable
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
        backref="corna",
    )

    # backrefs: posts


class PostTable(Base):
    """"Post Table."""

    __tablename__ = "posts"

    post_uuid = Column(
        UUID,
        primary_key=True,
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
        backref="posts",
    )
    mapper = relationship(
        "PostObjectMap",
        uselist=False,
        back_populates="post",
    )


class PostObjectMap(Base):
    """Maps posts to objects via post type field.

    Each post can only be one type of 'post' so this table
    will be quite sparse. At any given time only three columns
    will have an entry:
      - uuid
      - post_uuid
      - main object uuid
    """
    __tablename__ = "post_object_map"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    post_uuid = Column(
        UUID,
        ForeignKey("posts.post_uuid"),
        doc="Foreign key pointer to post table",
    )
    text_post_uuid = Column(
        UUID,
        ForeignKey("text_posts.uuid"),
        doc="Foreign key pointer to main text post object",
    )
    photo_post_uuid = Column(
        UUID,
        ForeignKey("photo_posts.uuid"),
        doc="Foreign key pointer to main photo post object",
    )
    post = relationship(
        "PostTable",
        back_populates="mapper",
    )
    text = relationship(
        "TextPost",
        back_populates="mapper",
    )
    photo = relationship(
        "PhotoPost",
        back_populates="mapper",
    )


class TextPost(Base):
    """Table for text posts."""

    __tablename__ = "text_posts"

    uuid = Column(
        UUID,
        primary_key=True
    )
    title = Column(
        Text,
        doc="Title of the text post"
    )
    body = Column(
        Text,
        doc="Body of the text post"
    )
    mapper = relationship(
        "PostObjectMap",
        uselist=False,
        back_populates="text",
    )


class PhotoPost(Base):
    """Table for picture posts."""

    __tablename__ = "photo_posts"

    uuid = Column(
        UUID,
        primary_key=True,
    )
    url_extension = Column(
        Text,
        index=True,
        unique=True,
        doc="The url extension of the picture, this will be used to"
            "load the picture on each corna",
    )
    path = Column(
        Text,
        doc="path to photo",
    )
    caption = Column(
        Text,
        doc="Optional caption associated with picture",
    )
    size = Column(
        Integer,
        doc="Size of file in bytes. This is essentially output of `stat`",
    )
    mapper = relationship(
        "PostObjectMap",
        uselist=False,
        back_populates="photo",
    )
