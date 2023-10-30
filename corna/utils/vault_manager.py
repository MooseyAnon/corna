"""API for interacting with the corna vault."""

from binascii import unhexlify
import json
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple, Union

import yaml

from corna.utils.crypto import VaultAES256

VAULT_PATH: str = os.environ.get(
    'ANSIBLE_VAULT_PATH',
    os.path.join(os.path.expanduser('~/vault'))
)
PASSWORD_PATH: str = os.environ.get(
    'ANSIBLE_VAULT_PASSWORD_FILE',
    os.path.join(os.path.expanduser('~/.vault-password'))
)

# Cache of decrypted data
_VAULT_DATA: Optional[Dict[str, Any]] = None

logger = logging.getLogger(__name__)


def decrypt_data(password: str, encrypted_data: bytes) -> Dict[str, Any]:
    """decrypt data in the vault.

    :param str password: password used for decryption
    :param bytes encrypted_data: raw data read directly from the vault
        file
    :return: unencrypted vault data
    :rtype: dict[str, any]
    :raises RuntimeError: is file headers are not as expected i.e
        not a valid ansible-vault file
    """
    header_fields: str = encrypted_data[0].rstrip().split(";")
    if header_fields[0] != "$ANSIBLE_VAULT":
        raise RuntimeError("Invalid header - bad format id")
    if header_fields[1] not in ("1.1", "1.2"):
        raise RuntimeError("Invalid header - bad version")
    if header_fields[2] != "AES256":
        raise RuntimeError("Invalid header - bad cipher")
    vaulttext = "".join(letter.rstrip() for letter in encrypted_data[1:])

    vaulttext_split: bytes = unhexlify(vaulttext).split(b"\n")

    if len(vaulttext_split) != 3:
        raise RuntimeError("Invalid number of parts to vaulttext")

    b_salt: str = unhexlify(vaulttext_split[0])
    b_crypted_hmac: str = unhexlify(vaulttext_split[1])
    b_ciphertext: str = unhexlify(vaulttext_split[2])

    decrypted: str = VaultAES256.decrypt(
        password, b_ciphertext, b_salt, b_crypted_hmac
    )

    data: Dict[str, Any] = yaml.safe_load(decrypted)
    return data


def get_decrypted_data() -> Dict[str, Any]:
    """Get the decrypted data from the vault.

    :returns: the decrypted data from the vault
    :rtype: dict
    :raises OSError: if either the password file or the vault itself do
        not exist
    """

    global _VAULT_DATA  # pylint: disable=global-statement
    if _VAULT_DATA is None:
        logger.debug('Decrypting Ansible Vault %r...', VAULT_PATH)

        try:
            with open(PASSWORD_PATH, 'r', encoding="utf-8") as password_file:
                password: str = password_file.read().strip().encode("utf-8")
        except IOError as e:
            raise OSError(f"Password file {PASSWORD_PATH!r} not found") from e

        try:
            with open(VAULT_PATH, "r", encoding="utf-8") as vault_file:
                encrypted_data: bytes = vault_file.readlines()
        except IOError as e:
            raise OSError(f"Vault file {VAULT_PATH!r} not found") from e

        _VAULT_DATA = decrypt_data(password, encrypted_data)

    return _VAULT_DATA


def get_item(key: Optional[str] = None) -> Any:
    """Get an item from the vault.

    If the vault hasn't yet been decrypted, this will be done first.
    If no key is given, the entire vault (under the 'vault' key) is returned.

    :param str key: the path to the item in the vault, e.g. `'service.password'`
    :returns: the value of the given vault item pointed at by ``key``
    :rtype: <any>
    :raises KeyError: if the key doesn't exist
    """
    keys = ['vault'] + (key.split('.') if key else [])
    data = get_decrypted_data()
    for crumb in keys:
        data = data[crumb]
    return data


def get_items(*keys: Tuple[str]) -> Tuple[Any]:
    """Get multiple items from the vault.

    :param tuple keys: the keys to get from the vault
    :returns: the values of the given vault items
    :rtype: tuple
    """
    return tuple(get_item(key) for key in keys)


def pretty_print(val: Union[str, object]) -> None:
    """Pretty-print ``val`` to `stdout`.

    :param val: the value/object to print
    :type val: Union[str, object]
    """
    if isinstance(val, (dict, list, tuple)):
        out = json.dumps(val, indent=2)
    else:
        out = val
    sys.stdout.write(f"{out}\n")
