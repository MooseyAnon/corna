"""Models for the Corna app."""

# pylint: disable=too-few-public-methods
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.exc import DetachedInstanceError


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
