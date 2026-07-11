"""Tests for Google Contacts token encryption round-trip."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.modules.google_contacts.crypto_utils import decrypt_token, encrypt_token


def test_encrypt_decrypt_round_trip() -> None:
    plaintext = "ya29.some-access-token-value"

    ciphertext = encrypt_token(plaintext)

    assert ciphertext != plaintext
    assert decrypt_token(ciphertext) == plaintext


def test_encrypt_is_not_deterministic_but_decrypts_consistently() -> None:
    plaintext = "1//refresh-token-value"

    ciphertext_a = encrypt_token(plaintext)
    ciphertext_b = encrypt_token(plaintext)

    assert ciphertext_a != ciphertext_b
    assert decrypt_token(ciphertext_a) == plaintext
    assert decrypt_token(ciphertext_b) == plaintext
