"""Integration tests for POST /congregations/{tenant_id}/address/geocode.

The Nominatim call itself is unit-tested in tests/unit/congregations/test_geocoding.py;
these tests cover the endpoint's auth, response shape, and that it never
writes to the database (it's a preview, not a save)."""

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

from app.common.id_utils import generate_id
from app.core.database import Base, get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.congregations import router as congregations_router
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.congregations.geocoding import GeocodeResult
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

OWNER_ID = "user-owner"
OUTSIDER_ID = "user-outsider"
TENANT_ID = "tenant-poznan"


def _api_user(user_id: str) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add(TenantDB(id=TENANT_ID, name="Zbór w Poznaniu", status="published", owner_id=OWNER_ID, created_at=now))
    session.add(TenantMembershipDB(tenant_id=TENANT_ID, user_id=OWNER_ID, role="owner"))
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=TENANT_ID,
            street="Stary Rynek 1",
            city="Poznań",
            country="PL",
            status="draft",
            created_at=now,
            updated_at=now,
        )
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

        yield client, login, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_geocode_preview_returns_coordinates_without_saving(ctx, monkeypatch) -> None:
    client, login, session_factory = ctx
    login(_api_user(OWNER_ID))

    async def _fake_geocode_address(**kwargs):
        return GeocodeResult(latitude=52.4064, longitude=16.9252, display_name="Poznań, Poland", confidence="exact")

    monkeypatch.setattr(congregations_router, "geocode_address", _fake_geocode_address)

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/address/geocode",
        json={"street": "Stary Rynek 1", "city": "Poznań", "country": "PL"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == pytest.approx(52.4064)
    assert body["longitude"] == pytest.approx(16.9252)
    assert body["confidence"] == "exact"

    # A preview must never write coordinates to the address row.
    async with session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == TENANT_ID))
        address = result.scalar_one()
        assert address.latitude is None
        assert address.longitude is None
        assert address.geocode_status == "pending"


@pytest.mark.asyncio
async def test_geocode_preview_not_found(ctx, monkeypatch) -> None:
    client, login, _session_factory = ctx
    login(_api_user(OWNER_ID))

    async def _fake_geocode_address(**kwargs):
        return None

    monkeypatch.setattr(congregations_router, "geocode_address", _fake_geocode_address)

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/address/geocode",
        json={"city": "Nieistniejące Miasto Xyz", "country": "PL"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "not_found"
    assert body["latitude"] is None


@pytest.mark.asyncio
async def test_geocode_preview_requires_tenant_access(ctx, monkeypatch) -> None:
    client, login, _session_factory = ctx
    login(_api_user(OUTSIDER_ID))

    async def _fake_geocode_address(**kwargs):
        raise AssertionError("Should not be called for an unauthorized user")

    monkeypatch.setattr(congregations_router, "geocode_address", _fake_geocode_address)

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/address/geocode",
        json={"city": "Poznań", "country": "PL"},
    )

    assert response.status_code == 403
