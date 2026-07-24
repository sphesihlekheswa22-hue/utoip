"""Password hashing helpers."""
from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def hash_secret(secret: str) -> str:
    return generate_password_hash(secret, method="pbkdf2:sha256")


def verify_secret(secret_hash: str, secret: str) -> bool:
    return check_password_hash(secret_hash, secret)
