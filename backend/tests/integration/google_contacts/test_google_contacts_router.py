"""Integration tests for the Google Contacts connection module.

Covers docs/plans/2026-07-10--google-contacts-sync.md Phase 1: only
admin/owner can connect/import (decision #1), and the contacts list is
filtered to "zbór"/"chwz" matches (decision #3) before reaching the client.
"""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_POOL_SIZE", "1")
os.environ.setdefault("DATABASE_MAX_OVERFLOW", "0")

from app.core.database import Base, get_db
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.google_contacts.oauth_provider import (
    GoogleContactsTokenResponse,
    google_contacts_oauth_provider,
)
from main import app

ADMIN_ID = "user-admin"
MEMBER_ID = "user-member"

RAW_CONTACTS = [
    {
        "resourceName": "people/c1",
        "organizations": [{"name": "Zbór CHWZ Kraków"}],
        "emailAddresses": [{"value": "krakow@chwz.example"}],
    },
    {
        "resourceName": "people/c2",
        "names": [{"displayName": "Anna Nowak", "givenName": "Anna", "familyName": "Nowak"}],
        "phoneNumbers": [{"value": "+48123456789"}],
    },
]


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> None:
    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin", is_admin=True),
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
        ]
    )
    await session.commit()


@pytest_asyncio.fixture
async def ctx():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, login

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_non_admin_cannot_get_auth_url(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post("/api/google-contacts/auth-url")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_gets_auth_url_with_readonly_scope(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post("/api/google-contacts/auth-url")

    assert response.status_code == 200
    body = response.json()
    assert "accounts.google.com" in body["authUrl"]
    assert "contacts.readonly" in body["authUrl"]
    assert body["state"]


@pytest.mark.asyncio
async def test_connection_status_defaults_to_disconnected(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get("/api/google-contacts/connection")

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "scope": None,
        "connectedAt": None,
        "expiresAt": None,
    }


@pytest.mark.asyncio
async def test_disconnect_without_connection_returns_404(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.delete("/api/google-contacts/connection")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_callback_stores_connection_then_contacts_are_filtered(ctx, monkeypatch) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    async def fake_exchange_code_for_token(code: str) -> GoogleContactsTokenResponse:
        assert code == "auth-code"
        return GoogleContactsTokenResponse(
            accessToken="access-token",
            tokenType="Bearer",
            scope="https://www.googleapis.com/auth/contacts.readonly",
            expiresIn=3600,
            refreshToken="refresh-token",
        )

    async def fake_list_connections(access_token: str) -> list[dict]:
        assert access_token == "access-token"
        return RAW_CONTACTS

    monkeypatch.setattr(google_contacts_oauth_provider, "exchange_code_for_token", fake_exchange_code_for_token)
    monkeypatch.setattr(google_contacts_oauth_provider, "list_connections", fake_list_connections)

    callback_response = await client.post("/api/google-contacts/callback", json={"code": "auth-code", "state": "some-state"})
    assert callback_response.status_code == 200
    assert callback_response.json()["connected"] is True
    assert callback_response.json()["scope"] == "readonly"

    status_response = await client.get("/api/google-contacts/connection")
    assert status_response.json()["connected"] is True

    contacts_response = await client.get("/api/google-contacts/contacts")
    assert contacts_response.status_code == 200
    body = contacts_response.json()
    assert body["totalFetched"] == 2
    assert body["matchedCount"] == 1
    assert body["contacts"][0]["resourceName"] == "people/c1"
    assert body["contacts"][0]["suggestedType"] == "church"

    disconnect_response = await client.delete("/api/google-contacts/connection")
    assert disconnect_response.status_code == 200
