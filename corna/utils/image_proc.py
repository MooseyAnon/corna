import hashlib
from typing import Callable

# Using md5 there seems to be some small chance of collisions
# however, my maths is not good enough to calculate it myself
# and there seems to be some conflicting points RE answers I've
# found online.
# For more discussion: https://stackoverflow.com/q/201705
DIGESTMOD: Callable = hashlib.md5
READ_BYTES: int = 8192


def hash_image(image_path: str) -> str:
    """Hash an image using the global digest algorithm.

    :param str image_path: path to the image
    :returns: hexadecimal representation of the hash
    :rtype: str
    """
    digest: object = DIGESTMOD()

    with open(image_path, "rb") as fd:
        while True:
            # read 8KB chunks
            nxt: bytes = fd.read(READ_BYTES)
            if not nxt:
                break
            digest.update(nxt)

    return digest.hexdigest()
