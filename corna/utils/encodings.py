"""Various encoding checkers/converters."""

import base64
from typing import Union


# this is lifted from and inspired by python pallets itsDangerous library
# https://github.com/pallets/itsdangerous/tree/main
class EncodingError(ValueError):
    """Raised when there is an issue encoding or decoding base64."""


def to_bytes(
    message: Union[bytes, str],
    encoding: str = "utf-8",
    errors: str = "strict",
) -> bytes:
    """Encode string to a given encoding.

    :param Union message: string to encode
    :param str encoding: the new encoding
    :param str errors: the error level to handle during encoding

    :return: the message as an encoded bytestring
    :rtype: bytes
    """
    if isinstance(message, str):
        message: bytes = message.encode(encoding, errors)
    return message


def from_bytes(
    message: Union[bytes, str],
    encoding: str = "utf-8",
    errors: str = "strict"
) -> str:
    """Decode a bytestring to a given encoding.

    :param Union message: string to decode
    :param str encoding: the new encoding
    :param str errors: the error level to handle during encoding

    :returns: message decoded to string
    :rtype: str
    """
    if isinstance(message, bytes):
        message: str = message.decode(encoding, errors)
    return message


def base64_encode(string: Union[bytes, str]) -> bytes:
    """Base64 encode a string.

    :param Union[bytes, str] string: the string to encode
    :returns: a URL safe, base64 encoded bytestring
    :rtype: bytes
    """
    string: bytes = to_bytes(string)
    return base64.urlsafe_b64encode(string).rstrip(b"=")


def base64_decode(string: Union[bytes, str]) -> bytes:
    """Base64 decode a URL safe string.

    :param  Union[bytes, str] string: string to decode
    :returns: base64 decoded bytestring
    :rtype: bytes
    :raises TypeError:
    :raise ValueError: Both errors are generic issue catchers
        one level below the the catch all Exception
        exception.
    """
    string: bytes = to_bytes(string, encoding="ascii", errors="ignore")
    string += b"=" * (-len(string) % 4)

    try:
        return base64.urlsafe_b64decode(string)
    except (TypeError, ValueError) as e:
        raise EncodingError(f"Error decoding base64 data: {e}") from e
