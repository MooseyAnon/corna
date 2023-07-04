"""Pytest fixtures for Corna unit tests."""
from contextlib import contextmanager
from pathlib import Path
import platform
import logging

from flask import _app_ctx_stack, request as flask_request
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import sqltap
import testing.postgresql

from corna.app import create_app
from corna.db import models
logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Pytest command line options accessible inside the fixtures."""
    parser.addoption(
        '--use-sql-files',
        action='store_true',
        help="Use static SQL files to create/drop db in fixture"
    )
    parser.addoption(
        '--sql-profile',
        action='store_true',
        help="Generate SQL profile for each test",
    )


@contextmanager
def test_db_engine():
    """Context manager for session-wide test database."""
    if platform.system() == 'Darwin':
        # later versions of mac it might be:
        # '/usr/local/opt/postgresql@10/bin'
        postgresql_path = Path(
            "/Applications/Postgres.app/Contents/Versions/latest/bin")
    elif Path('/usr/lib/postgresql/10/bin').exists():
        postgresql_path = Path('/usr/lib/postgresql/11/bin')
    else:
        postgresql_path = Path('/usr/pgsql-11/bin')

    initdb_path = postgresql_path / 'initdb'
    postgres_path = postgresql_path / 'postgres'

    logger.info("Create test postgres instance")
    with testing.postgresql.Postgresql(
            initdb=initdb_path,
            postgres=postgres_path
    ) as postgresql:
        print("postgres created!!!!")
        engine = create_engine(
            postgresql.url(),
            connect_args={"options": "-c timezone=utc"}
        )
        with engine.connect() as connection:
            connection.execute("CREATE EXTENSION hstore;")
        yield engine
        logging.debug("Delete test postgres instance")


@pytest.fixture(name='engine', scope='session')
def _engine():
    """Session-wide test database."""
    with test_db_engine() as engine:
        yield engine

@pytest.fixture(name='session_class')
def _session_class(engine, request):
    """Session fixture.

    The engine uses either the ORM models or SQL files to create the schema,
    depending on the `--use-sql-files` flag.
    """
    use_sql_files = request.config.getoption('--use-sql-files')

    logging.debug("Create all tables")
    if use_sql_files:
        models_to_sql.create_all_from_sql(engine)
    else:
        models.Base.metadata.create_all(engine)

    yield sessionmaker(bind=engine)

    logging.debug("Remove all tables and data")
    if use_sql_files:
        models_to_sql.drop_all_from_sql(engine)
    else:
        models.Base.metadata.drop_all(engine)


@pytest.fixture(name='session')
def _session(session_class):
    """Creates an empty database for a test."""
    app_scoped_session = scoped_session(
        session_class,
        scopefunc=_app_ctx_stack.__ident_func__
    )

    yield app_scoped_session
    app_scoped_session.rollback()  # pylint: disable=no-member


@pytest.fixture(name='client')
def _client(session, request):
    """Provide access to the Flask app."""
    app = create_app(session)
    app.config['TESTING'] = True

    # Profile the app if required
    if request.config.getoption('sql_profile'):
        profiler = FlaskSqlProfiler(request.node.name)
        app.before_request(profiler.start)
        app.after_request(profiler.end)

    yield app.test_client()


@pytest.fixture(name="user")
def _create_user(client):
    resp = client.post("/api/v1/register", json=single_user())
    assert resp.status_code == 201
    logger.debug("created user")


@pytest.fixture(name="login")
def _create_and_login_user(client, user):
    user_deets = single_user()
    email = user_deets["email_address"]
    password = user_deets["password"]

    resp = client.post("/api/v1/login", json={
            "email_address": email,
            "password": password,
        }
    )
    assert resp.status_code == 200
    logger.debug("logged in user")
