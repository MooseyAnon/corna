"""Corna session configuration."""

from contextlib import contextmanager
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm import sessionmaker

from corna.utils import vault_item

from . import models

logger = logging.getLogger(__name__)


def get_sqlalchemy_url():
    """Return the Shifts database URL consumed by the SQLAlchemy engine.

    The Shifts service environment defines $DB_SERVER and $DB_USER
    variables for both production and staging instances of the app. These
    variables are used to construct a URL which points to an "official" shifts
    database instance. These variables can be defined as appropriate by a user
    for local testing.

    :raises RuntimeError: if either $DB_SERVER or $DB_USER are not defined
    :raises KeyError: if $DB_USER does not correspond with a password known in
        the vault
    :returns: the PostgreSQL URL e.g.
        "postgresql://<user>:<pass>:<host>:<port>/<database>"
    :rtype: str
    """
    db_address = os.getenv("DB_ADDRESS")
    db_user = os.getenv("DB_USER")
    if not (db_address and db_user):
        raise RuntimeError(
            "The environment variables DB_ADDRESS or DB_USER are not "
            "defined")

    db_password = vault_item(f"postgres.{db_user}")
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    sqlalchemy_url = (
        f"postgresql://{db_user}:{db_password}"
        f"@{db_address}:{db_port}/{db_name}"
    )
    ssl_mode = os.getenv("SSL_MODE")
    if ssl_mode:
        sqlalchemy_url = f"{sqlalchemy_url}?sslmode={ssl_mode}"

    logger.info(
        "Connecting using %r", sqlalchemy_url.replace(db_password, '*****'))
    return sqlalchemy_url


def session_maker(application_name="corna", statement_timeout_secs=None):
    """Create a custom database session class.

    The session is customised with an application name, and a statement timeout
    for long-running queries.

    :param str application_name: the name of the application.
    :param int statement_timeout_secs: the number of seconds allowed for an SQL
        query to complete. If `None`, no timeout is configured.
    :returns: the custom session class
    :rtype: sqlalchemy.Session
    """
    echo = os.getenv("SQLALCHEMY_ECHO") == "1"

    connect_args = {
        "application_name": application_name,
    }
    engine = create_engine(
        get_sqlalchemy_url(), echo=echo, connect_args=connect_args)

    logger.info("Successfully created engine")

    if statement_timeout_secs is not None:
        statement_timeout_ms = int(statement_timeout_secs * 1000)
        set_statement = f"SET statement_timeout={statement_timeout_ms}"

        # 'engine_connect' seems to be the least frequent event where
        # 'SET statement_timeout' will persist. The 'connect' event registers
        # the first time the pool connects to the db, but the statement_timeout
        # only lasts for the first query on each connection.
        @listens_for(engine, "engine_connect")
        def set_timeout(connection, _):
            connection.execute(set_statement)

    logger.info("Creating tables")
    # create tables
    models.Base.metadata.create_all(engine)
    logger.info("Tables have been created")
    return sessionmaker(bind=engine, expire_on_commit=False)
