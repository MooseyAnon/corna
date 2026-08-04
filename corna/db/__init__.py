"""Corna session configuration."""

from contextlib import contextmanager
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm import sessionmaker

from . import models

logger = logging.getLogger(__name__)


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
    # Import lazily to avoid the config <-> vault module import cycle.
    # This is safe because vault access happens only after configuration
    # loading has completed.
    from corna.config import get_config  # pylint: disable=C0415

    echo = get_config().app.sqlalchemy_echo
    sqlalchemy_url = get_config().database.url
    logger.info(
        "Connecting using %r", get_config().database.connection_details)

    connect_args = {
        "application_name": application_name,
    }
    engine = create_engine(
        sqlalchemy_url, echo=echo, connect_args=connect_args)

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

    logger.info("Successfully created session")
    return sessionmaker(bind=engine, expire_on_commit=False)
