"""SQLAlchemy column type + blind-index helpers for encrypting PII at rest.

Reuses the Fernet + PBKDF2-derived-key pattern already used by
two_factor/crypto_utils.py and google_contacts/crypto_utils.py, but applies
it transparently at the ORM boundary via a TypeDecorator so callers reading
model attributes (PersonDB.first_name, CongregationAddressDB.street, ...)
never see ciphertext and can't forget to decrypt it themselves.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import Text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


def _key_source() -> str:
    return os.getenv("PII_ENCRYPTION_KEY") or settings.security.secret_key


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Cached so the 100k-iteration PBKDF2 derivation runs once per process,
    not once per encrypted field per row (this type decrypts on every load)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"pii_encryption_salt_v1",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(_key_source().encode()))
    return Fernet(key)


@lru_cache(maxsize=1)
def _blind_index_key() -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"pii_blind_index_salt_v1",
        iterations=100_000,
    )
    return kdf.derive(_key_source().encode())


def hmac_email(email: str | None) -> str | None:
    """Deterministic blind index for exact-match e-mail lookups on an
    otherwise-encrypted column (see PersonDB.email_bidx)."""
    if not email:
        return None
    normalized = email.strip().lower()
    return hmac.new(_blind_index_key(), normalized.encode(), hashlib.sha256).hexdigest()


def hmac_phone_digits(phone: str | None) -> str | None:
    """Deterministic blind index for exact-match phone lookups on an
    otherwise-encrypted column (see PersonDB.phone_bidx).

    Normalizes to digits-only, matching the comparison
    `ChurchRepository.find_person_by_email_or_phone` already did against the
    plaintext column before it was encrypted.
    """
    digits = re.sub(r"\D", "", phone) if phone else ""
    if not digits:
        return None
    return hmac.new(_blind_index_key(), digits.encode(), hashlib.sha256).hexdigest()


def encrypt_value(plaintext: str) -> str:
    """Encrypt a single value with the same key/scheme EncryptedString uses.

    Exposed for migrations/072_encrypt_person_pii.py, which encrypts existing
    rows via raw SQL UPDATEs rather than the ORM (see that file for why).
    """
    return _fernet().encrypt(plaintext.encode()).decode()


def is_encrypted_value(value: str) -> bool:
    """True if `value` already decrypts as a Fernet token from this key.

    Lets the migration skip rows a previous (possibly interrupted) run
    already encrypted, so it's safe to re-run.
    """
    try:
        _fernet().decrypt(value.encode())
        return True
    except InvalidToken:
        return False


class EncryptedString(TypeDecorator[str]):
    """Transparently Fernet-encrypts a string column at rest.

    Backed by Text rather than a bounded VARCHAR: Fernet ciphertext is
    considerably longer than the plaintext it replaces (a 255-char name
    encrypts to 400+ chars), so a bounded column would truncate/reject it.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # A row not yet migrated by migrations/072_encrypt_person_pii.py
            # still holds plaintext — return it as-is instead of raising, so
            # the batched/online migration doesn't 500 every request for the
            # rows it hasn't reached yet.
            return value

    def process_literal_param(self, value: str | None, dialect: Dialect) -> str:
        raise NotImplementedError("EncryptedString does not support inline literal binding")

    @property
    def python_type(self) -> type[str]:
        return str
