"""Feed change detection: sha256 over raw payload bytes."""

import hashlib


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
