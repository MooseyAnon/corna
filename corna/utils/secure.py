"""Security oriented utils."""
import logging
import secrets
import time
from typing import Any, Dict

from sqlalchemy import exists

logger = logging.getLogger(__name__)


class UnableToGenerateUnqiqueToken(ValueError):
    """Unable to generate a unique secure token"""


def session_token() -> str:
    """URL safe session token

    :return: a web safe session token
    :rtype: str
    """
    return secrets.token_urlsafe()


def token_unique(session: Any, column: Any, token: str) -> bool:
    """Checks if token already exists.

    The secret modules `urlsafe` function isnt guaranteed to be
    unqiue, so we want to check if the same token already exists.

    :param sqlalchemy.Session session: a db session
    :param sqlalchemy.Table.column column: name of column to search on e.g.
        UserTable.email_address
    :returns: True if token is unqiue, else False
    :rtype: bool
    """
    return not session.query(exists().where(column == token)).scalar()


def generate_unique_token(
    session: Any, column: Any, tries: int = 10
) -> str:
    """Generate unique token.

    Generates cookie and session tokens.

    :param sqlalchemy.Session session: db session
    :param sqlalchemy.Table.column column: name of column to search on e.g.
        UserTable.email_address
    :param int tries: the number of tries before giving up

    :returns: a unique token if possible
    :rtype: str
    :raises UnableToGenerateUnqiqueToken:
    """
    i: int = 0
    while i < tries:
        token: str = session_token()
        if token_unique(session, column, token):
            return token

        logger.warning("Generated duplicate token, trying again")
        # we dont want the loop to be too tight as this is making
        # requests to the database
        time.sleep(0.1)
        i += 1

    raise UnableToGenerateUnqiqueToken("Unable to generate unique token")


def secure_headers() -> Dict[str, str]:
    """Secure headers map.

    :returns: a mapping of secure headers
    :rtype: dict[str, str]
    """
    headers: Dict[str, str] = {}
    # default security headers
    headers['Content-Security-Policy'] = "default-src 'self'"
    headers['Strict-Transport-Security'] = "max-age=31536000; includeSubDomains"
    headers['X-Content-Type-Options'] = "nosniff"
    headers['X-Frame-Options'] = "SAMEORIGIN"
    headers['X-XSS-Protection'] = "1; mode=block"

    # add cors stuff
    headers.update(cors_headers())
    return headers


def cors_headers() -> Dict[str, str]:
    """CORS headers map.

    :returns: a mapping of CORS headers
    :rtype: dict[str, str]
    """
    headers: Dict[str, str] = {}
    headers["Access-Control-Allow-Origin"] = "*"
    headers["Access-Control-Allow-Credentials"] = True
    headers["Access-Control-Allow-Headers"] = "*"
    headers["Access-Control-Allow-Methods"] = True
    return headers
