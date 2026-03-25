import pytest

from app.utils.security import get_password_hash, verify_password


def test_get_password_hash_accepts_password_over_72_bytes():
    too_long = "a" * 200
    hashed = get_password_hash(too_long)
    assert verify_password(too_long, hashed) is True
