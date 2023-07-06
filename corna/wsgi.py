"""A Corna app is created in this module."""
from .app import create_app
from .db import session_maker

session = session_maker(
    application_name='Corna', statement_timeout_secs=300)
app = create_app(session)
