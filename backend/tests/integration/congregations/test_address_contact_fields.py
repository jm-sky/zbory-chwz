"""Tests for the congregation address website/email/iban fields:
- website gets an https:// scheme prepended if missing
- a bare Polish NRB gets normalized to a full IBAN with the "PL" prefix
- invalid e-mail/IBAN values are rejected with 422
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
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

OWNER_ID = "user-owner"
TENANT_ID = "tenant-poznan"


def _api_user(user_id: str) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add(TenantDB(id=TENANT_ID, name="Zbór w Poznaniu", status="published", owner_id=OWNER_ID, created_at=now))
    session.add(TenantMembershipDB(tenant_id=TENANT_ID, user_id=OWNER_ID, role="owner"))
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
    app.dependency_overrides[get_current_user] = lambda: _api_user(OWNER_ID)

    async with session_factory() as session:
        await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_address_normalizes_website_and_bare_polish_nrb(ctx) -> None:
    response = await ctx.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={
            "city": "Poznań",
            "country": "PL",
            "status": "draft",
            "website": "example.pl",
            "email": "kontakt@example.pl",
            "iban": "61 1090 1014 0000 0712 1981 2874",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["website"] == "https://example.pl"
    assert body["email"] == "kontakt@example.pl"
    assert body["iban"] == "PL61109010140000071219812874"


@pytest.mark.asyncio
async def test_create_address_keeps_a_foreign_iban_prefix(ctx) -> None:
    response = await ctx.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={"city": "Poznań", "country": "PL", "status": "draft", "iban": "DE89 3704 0044 0532 0130 00"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["iban"] == "DE89370400440532013000"


@pytest.mark.asyncio
async def test_create_address_rejects_invalid_iban_checksum(ctx) -> None:
    response = await ctx.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={"city": "Poznań", "country": "PL", "status": "draft", "iban": "PL61109010140000071219812875"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_address_rejects_invalid_email(ctx) -> None:
    response = await ctx.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={"city": "Poznań", "country": "PL", "status": "draft", "email": "not-an-email"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_address_sets_iban_and_website(ctx) -> None:
    created = await ctx.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={"city": "Poznań", "country": "PL", "status": "draft"},
    )
    assert created.status_code == 201

    response = await ctx.patch(
        f"/api/congregations/{TENANT_ID}/address",
        json={"website": "https://example.pl", "iban": "61109010140000071219812874"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["website"] == "https://example.pl"
    assert body["iban"] == "PL61109010140000071219812874"
