"""API for interacting with the corna vault."""

from binascii import unhexlify
import logging
from typing import Any, Dict
import yaml

from corna.utils.crypto import VaultAES256

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
    vaulttext = "".join(l.rstrip() for l in encrypted_data[1:])

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
