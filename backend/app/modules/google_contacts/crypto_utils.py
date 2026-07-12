"""Symmetric encryption for stored Google Contacts OAuth tokens."""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """Derive a Fernet key from dedicated GOOGLE_CONTACTS_ENCRYPTION_KEY or SECRET_KEY."""

    key_source = os.getenv("GOOGLE_CONTACTS_ENCRYPTION_KEY") or settings.security.secret_key

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"google_contacts_salt_v1",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(key_source.encode()))


def encrypt_token(plaintext: str) -> str:
    """Encrypt an OAuth token with Fernet."""

    fernet = Fernet(_get_encryption_key())
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt an OAuth token with Fernet."""

    fernet = Fernet(_get_encryption_key())
    return fernet.decrypt(ciphertext.encode()).decode()
