"""Tests for GoogleContactsOAuthProvider authorization URL building."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from urllib.parse import parse_qs, urlparse

from app.modules.google_contacts.oauth_provider import (
    SCOPE_READONLY,
    SCOPE_WRITE,
    GoogleContactsOAuthProvider,
)


def test_authorization_url_requests_readonly_scope_only_by_default() -> None:
    provider = GoogleContactsOAuthProvider()

    url = provider.get_authorization_url("state-123")

    query = parse_qs(urlparse(url).query)
    assert query["state"] == ["state-123"]
    assert query["scope"] == [SCOPE_READONLY]
    assert query["access_type"] == ["offline"]


def test_authorization_url_requests_write_scope_when_asked() -> None:
    provider = GoogleContactsOAuthProvider()

    url = provider.get_authorization_url("state-456", write=True)

    query = parse_qs(urlparse(url).query)
    assert query["scope"] == [f"{SCOPE_READONLY} {SCOPE_WRITE}"]
