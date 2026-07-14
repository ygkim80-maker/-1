import hashlib


def sha256_hex(*parts: bytes) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part)
    return h.hexdigest()
