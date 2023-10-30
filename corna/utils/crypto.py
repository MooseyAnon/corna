"""
Handles the decryption of the ansible vault.

Based on code and docs in ansible
https://github.com/ansible/ansible/blob/devel/lib/ansible/parsing/vault/__init__.py
https://docs.ansible.com/ansible/latest/user_guide/vault.html

"""

# This is third-party code so skip
# pylint: skip-file

import warnings

try:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            action='ignore',
            message='Python 3.6 is no longer supported'
        )
        from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.primitives.ciphers import (
        Cipher as C_Cipher, algorithms, modes)
    from cryptography.hazmat.primitives.hmac import HMAC
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError as error:
    raise (error)


class VaultAES256:

    """
    Vault implementation using AES-CTR with an HMAC-SHA256 authentication code.
    Keys are derived using PBKDF2
    """

    # http://www.daemonology.net/blog/2009-06-11-cryptographic-right-answers.html

    # Note: strings in this class should be byte strings by default.

    @staticmethod
    def _create_key_cryptography(b_password, b_salt, key_length, iv_length):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=2 * key_length + iv_length,
            salt=b_salt,
            iterations=10000,
            backend=default_backend(),
        )
        b_derivedkey = kdf.derive(b_password)

        return b_derivedkey

    @staticmethod
    def _pbkdf2_prf(p, s):
        hash_function = SHA256_pycrypto
        return HMAC_pycrypto.new(p, s, hash_function).digest()

    @classmethod
    def _gen_key_initctr(cls, b_password, b_salt):
        # 16 for AES 128, 32 for AES256
        key_length = 32

        # AES is a 128-bit block cipher, so IVs and counter nonces are 16 bytes
        iv_length = algorithms.AES.block_size // 8

        b_derivedkey = cls._create_key_cryptography(
            b_password, b_salt, key_length, iv_length
        )
        b_iv = b_derivedkey[(key_length * 2): (key_length * 2) + iv_length]

        b_key1 = b_derivedkey[:key_length]
        b_key2 = b_derivedkey[key_length: (key_length * 2)]

        return b_key1, b_key2, b_iv

    @classmethod
    def _decrypt_cryptography(
        cls, b_ciphertext, b_crypted_hmac, b_key1, b_key2, b_iv
    ):
        # b_key1, b_key2, b_iv = self._gen_key_initctr(b_password, b_salt)
        # EXIT EARLY IF DIGEST DOESN'T MATCH
        hmac = HMAC(b_key2, hashes.SHA256(), default_backend())
        hmac.update(b_ciphertext)
        hmac.verify(b_crypted_hmac)

        cipher = C_Cipher(
            algorithms.AES(b_key1), modes.CTR(b_iv), default_backend()
        )
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        b_plaintext = (
            unpadder.update(
                decryptor.update(b_ciphertext) + decryptor.finalize()
            )
            + unpadder.finalize()
        )

        return b_plaintext

    @classmethod
    def decrypt(cls, b_password, b_ciphertext, b_salt, b_crypted_hmac):
        b_key1, b_key2, b_iv = cls._gen_key_initctr(b_password, b_salt)
        b_plaintext = cls._decrypt_cryptography(
            b_ciphertext, b_crypted_hmac, b_key1, b_key2, b_iv
        )
        return b_plaintext
