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
    email = relationship("EmailTable", back_populates="user")
    # backrefs: blog


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
