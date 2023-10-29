from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from corna.utils import vault_item

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from corna.db import models

target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# alembic expects the full URL (including the password) to be in plain
# text in the alembic.ini file. We could generate the alembic.ini file
# from a template when needed but there is the risk that it could be
# checked into git and become public. Here we securely generate the
# url and override the value inside the alembic.ini config.
db_address = os.getenv("DB_ADDRESS")
db_user = os.getenv("DB_USER")
if not(db_address and db_user):
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

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = sqlalchemy_url
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # this overrides the `sqlalchemy.url` prefixed url in the
        # config file
        url=sqlalchemy_url,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
