# auth/hash.py
from passlib.hash import argon2
from pydantic import SecretStr
from typing import Any

def unwrap_secret(val: Any) -> str:
    return val.get_secret_value() if isinstance(val, SecretStr) else str(val)

def hash_password(password: Any) -> str:
    plain = unwrap_secret(password)
    return argon2.hash(plain)

def verify_password(password: Any, hashed: str) -> bool:
    plain = unwrap_secret(password)
    return argon2.verify(plain, hashed)
