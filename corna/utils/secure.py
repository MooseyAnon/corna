"""Security oriented utils."""
import datetime
import hashlib
import hmac
import logging
import secrets
import time
from typing import Any, Callable, Dict, Tuple, Union

from dateutil.parser import parse
from sqlalchemy import exists

from corna.utils import future, get_utc_now
from corna.utils import encodings
from corna.utils import vault_item
from corna.utils.encodings import EncodingError

logger = logging.getLogger(__name__)

SPLITTR: bytes = b"||"
# hashing function used in HMAC signature
DIGESTMOD: Callable = hashlib.sha256


class UnableToGenerateUnqiqueToken(ValueError):
    """Unable to generate a unique secure token"""


class BadSignature(ValueError):
    """Signed message is not legit."""


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
    :param str token: the token to check for
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
    :param Callable func: token generation function

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
    :raises KeyError: if either salt or secret-key are not found
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
    expiry_date: bytes = encodings.to_bytes(future().isoformat())

    key: bytes = get_signed_key()
    message: bytes = encodings.to_bytes(message)

    mac: bytes = _sign(key, message=message).digest()
    encoded_mac: bytes = encodings.base64_encode(mac)

    encoded_signature: bytes = encodings.base64_encode(
        expiry_date
        + SPLITTR
        + message
        + SPLITTR
        + encoded_mac
    )
    return encoded_signature


def verify(
    original_message: Union[bytes, str],
    signature: Union[bytes, str],
) -> bool:
    """Verify original message or signature have not been tampered with.

    :param Union[bytes, str] original_message: the message that got signed
    :param Union[bytes, str] signature: the expected signature
    :return: true if signature is valid
    :rtype: bool
    :raises BadSignature: yeet out if anything goes wrong, we dont really
        care exactly what it is.
    """
    try:
        signature: bytes = encodings.base64_decode(signature)

    except EncodingError as e:
        raise BadSignature from e

    signed_original_message: bytes = _sign(
        get_signed_key(),
        message=encodings.to_bytes(original_message),
    ).digest()

    compare_result: bool =  hmac.compare_digest(
        signature, signed_original_message
    )
    return compare_result


def unsign(signature: Union[bytes, str]) -> Tuple[bytes, bytes, bytes]:
    """Unsign a signed messaged.

    :param Union[bytes, str] signature:
    :returns: the original message and its expected hash value
    :rtype: Tuple[bytes, bytes]
    :raises BadSignature:
    """
    message: bytes
    hash_value: bytes
    expiry_date: bytes

    try:
        signature: bytes = encodings.base64_decode(signature)

    except EncodingError as e:
        raise BadSignature(e) from e

    if not SPLITTR in signature:
        raise BadSignature(f"no {SPLITTR!r} found in signature")

    expiry_date, message, hash_value = signature.rsplit(SPLITTR)

    return expiry_date, message, hash_value


def expired(iso_datetime: Union[bytes, str]) -> bool:
    """Check if ISO 8601 formatted datetime is in the past.

    :param Union[bytes, str] iso_datetime: iso formatted datetime
    :returns: True if iso_datetime is in the past i.e. expired
    :rtype: bool
    """
    parsed_datetime: datetime.datetime = parse(iso_datetime)
    now: datetime.datetime = get_utc_now()
    return now > parsed_datetime


def is_valid(signature: Union[bytes, str]) -> bool:
    """Check if a signature is valid.

    :param Union[bytes, str] signature: signature to validate
    :return: true if signature is valid
    :rtype: bool
    """
    message: bytes
    hash_value: bytes
    expiry_date: bytes
    valid: bool

    try:
        expiry_date, message, hash_value = unsign(signature)
        valid = verify(message, hash_value) and not expired(expiry_date)

    except BadSignature as e:
        logger.error(e)
        valid = False

    return valid


def decoded_message(signature: bytes, encoding: str = "utf-8") -> str:
    """Get original messaged decoded to a string.

    :param bytes signature: the signed message to decode
    :param str encoding: the encoding to use, defaults to UTF-8

    :returns: the original, unsigned messaged decoded to string
    :rtype: str
    :raises BadSigniture: if signature is incorrect
    """
    message: bytes
    _, message, _ = unsign(signature)
    original_message: str = encodings.from_bytes(message, encoding=encoding)
    return original_message
