"""
Encrypt/decrypt TOTP shared secrets at rest using Fernet (key derived from ENCRYPTION_KEY).
"""
import base64
import hashlib
from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    raw = settings.ENCRYPTION_KEY.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_totp_secret(plain_secret: str) -> str:
    """Return URL-safe token string to store in MongoDB."""
    return _fernet().encrypt(plain_secret.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(token: str) -> str:
    """Decrypt stored token back to base32 secret string."""
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
