"""Security oriented utils."""
import hashlib
import hmac
import logging
import secrets
import time
from typing import Any, Callable, Dict, Union

from sqlalchemy import exists

from corna.utils import encodings
from corna.utils import vault_item
logger = logging.getLogger(__name__)

SPLITTR: bytes = b"||"
# hashing function used in HMAC signature
DIGESTMOD: Callable = hashlib.sha256


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
    session: Any, column: Any, tries: int = 10, func: Callable = session_token
) -> str:
    """Generate unique token using a given function.

    Generates cookie and session tokens. Also used to generate
    "unique-ish" url extensions for pictures.

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
        token: str = func()
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


# this is lifted from and inspired by python pallets itsDangerous library
# https://github.com/pallets/itsdangerous/tree/main
def _sign(key: bytes, message: Union[bytes] = None) -> object:
    """Return a new HMAC object ready to be signed.

    We dont do the signing here as there are occasions where the caller
    wants to modify the HMAC before signing e.g. to add a salt.

    :param bytes key: the secret key for the HMAC
    :param Union[bytes] message: message to add as part of the signing
    :returns: a new HMAC object ready to be signed
    :rtype: object
    """
    return hmac.new(
        key,
        msg=message,
        digestmod=DIGESTMOD
    )


def get_signed_key() -> bytes:
    """Get a signed and salted secret key.

    This function retrieves the secret key, salts it and
    hashes it before it is used as part of the message signing.

    :returns: bytestring representing the signed and salted secret-key
    :rtype: bytes
    :raises keyError: if either salt or secret-key are not found
    """
    try:
        salt: bytes = encodings.to_bytes(
            vault_item("keys.cornauser.salt")
        )
        key: bytes = encodings.to_bytes(
            vault_item("keys.cornauser.secret-key")
        )

    except KeyError as e:
        raise e

    signed_key: object = _sign(key)
    signed_key.update(salt)
    return signed_key.digest()


def sign(message: Union[bytes, str]) -> bytes:
    """Sign a given message using a secret key.

    :param Union[bytes, str] message: message to sign
    :returns: a bytestring representing the signed message
    :rtype: bytes
    """
    key: bytes = get_signed_key()
    message: bytes = encodings.to_bytes(message)

    mac: bytes = _sign(key, message=message).digest()
    encoded_signature: bytes = encodings.base64_encode(mac)

    return message + SPLITTR + encoded_signature
