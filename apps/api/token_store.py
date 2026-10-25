"""Encrypt refresh tokens with an external Fernet key; never log credentials."""
import os

from cryptography.fernet import Fernet


def cipher() -> Fernet:
    key = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required to connect Gmail")
    return Fernet(key.encode())


def encrypt(token: str) -> str:
    return cipher().encrypt(token.encode()).decode()


def decrypt(token: str) -> str:
    return cipher().decrypt(token.encode()).decode()
