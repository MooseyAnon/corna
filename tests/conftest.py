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
from tests.shared_data import blog_info, single_user


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
        # later versions of mac it might be (this is were brew puts it):
        # '/usr/local/opt/postgresql@10/bin'
        postgresql_path = Path(
            "/Applications/Postgres.app/Contents/Versions/12/bin")
    elif Path('/usr/lib/postgresql/12/bin').exists():
        postgresql_path = Path('/usr/lib/postgresql/12/bin')
    else:
        postgresql_path = Path('/usr/pgsql-12/bin')

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


@pytest.fixture(name="blog")
def _create_blog_for_logged_in_user(client, login):
    resp = client.post(
        f"/api/v1/corna/{blog_info['domain_name']}",
        json={"title": blog_info["title"]},
    )
    assert resp.status_code == 201


@pytest.fixture(name="sec_headers", autouse=True)
def _secure_headers(mocker):
    # mock out secure headers
    mocker.patch("corna.utils.secure.secure_headers", return_value={})


@pytest.fixture(autouse=True)
def _clear_all_envvars(monkeypatch):
    """Clear all the env vars needed for vault access.

    This prevents leakage from the users environment into the tests. Where
    needed tests will patch as required.
    """
    monkeypatch.delenv("ANSIBLE_VAULT_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("ANSIBLE_VAULT_PATH", raising=False)


class FlaskSqlProfiler:
    """Class to handle profiling of Flask SQL.

    The `start` and `end` are expected to be used as Flask `before_request`
    and `after_request` hooks.
    """

    def __init__(self, name):
        """Constructor.

        :param str name: A unique name for this profiling (e.g. the test name)
        """
        self.name = name
        self.count = 0
        self.sqltap = None
        logging.debug("Running with SQL profiling")

    def start(self):
        """Start the profiler."""
        self.sqltap = sqltap.start()

    def end(self, flask_resp):
        """Collect and output profiler stats.

        Parameter is required by Flask and is passed through unmodified.

        :param flask.Flask.response_class flask_resp: response from flask

        :returns: Flask response
        :rtype: flask.Flask.response_class
        """
        statistics = self.sqltap.collect()
        output_filename = f"sql_profile__{self.name}__{self.count}.html"
        self.count += 1
        logging.info(
            "Call to %s %s Generated SQL profile to %s",
            flask_request.method, flask_request.path, output_filename)
        sqltap.report(statistics, output_filename)
        return flask_resp
