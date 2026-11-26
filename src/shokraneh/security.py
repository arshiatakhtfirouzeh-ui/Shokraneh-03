"""PIN hashing helpers (the PIN only gates the UI; it does not encrypt files)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ROUNDS = 150_000


def hash_pin(pin: str, salt: bytes | None = None, rounds: int = _ROUNDS) -> dict:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, rounds)
    return {"salt": salt.hex(), "hash": digest.hex(), "rounds": rounds}


def verify_pin(pin: str, record: dict | None) -> bool:
    if not record:
        return False
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
        rounds = int(record.get("rounds", _ROUNDS))
    except (KeyError, ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(actual, expected)
