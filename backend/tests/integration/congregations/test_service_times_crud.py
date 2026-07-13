"""Integration tests for the service-times CRUD endpoints, including the
optional `description` field."""

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

MEMBER_ID = "user-member"
CHURCH_ID = "church-service-times"
OTHER_CHURCH_ID = "church-service-times-other"


def _api_user(user_id: str) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=False, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    for church_id in (CHURCH_ID, OTHER_CHURCH_ID):
        session.add(TenantDB(id=church_id, name="Zbor Testowy", status="published", owner_id=MEMBER_ID, created_at=now))
        session.add(TenantMembershipDB(tenant_id=church_id, user_id=MEMBER_ID, role="member"))
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
    app.dependency_overrides[get_current_user] = lambda: _api_user(MEMBER_ID)

    async with session_factory() as session:
        await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_service_time_with_description_round_trips(ctx) -> None:
    client = ctx

    response = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "sobota", "time": "21:00", "description": "Modlitwa nocna", "order": 0},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["day"] == "sobota"
    assert body["time"] == "21:00"
    assert body["description"] == "Modlitwa nocna"

    listed = await client.get(f"/api/congregations/{CHURCH_ID}/service-times")
    assert listed.status_code == 200
    assert listed.json()[0]["description"] == "Modlitwa nocna"


@pytest.mark.asyncio
async def test_create_service_time_without_description_defaults_to_none(ctx) -> None:
    client = ctx

    response = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "niedziela", "time": "10:00"},
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.asyncio
async def test_update_service_time_changes_fields_and_round_trips(ctx) -> None:
    client = ctx

    created = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "sobota", "time": "21:00", "description": "Modlitwa nocna", "order": 0},
    )
    service_time_id = created.json()["id"]

    response = await client.patch(
        f"/api/congregations/{CHURCH_ID}/service-times/{service_time_id}",
        json={"time": "22:00", "description": "Modlitwa poranna"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == service_time_id
    assert body["day"] == "sobota"
    assert body["time"] == "22:00"
    assert body["description"] == "Modlitwa poranna"

    listed = await client.get(f"/api/congregations/{CHURCH_ID}/service-times")
    assert listed.json()[0]["time"] == "22:00"
    assert listed.json()[0]["description"] == "Modlitwa poranna"


@pytest.mark.asyncio
async def test_update_service_time_partial_leaves_other_fields_unchanged(ctx) -> None:
    client = ctx

    created = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "sobota", "time": "21:00", "description": "Modlitwa nocna", "order": 3},
    )
    service_time_id = created.json()["id"]

    response = await client.patch(
        f"/api/congregations/{CHURCH_ID}/service-times/{service_time_id}",
        json={"day": "niedziela"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["day"] == "niedziela"
    assert body["time"] == "21:00"
    assert body["description"] == "Modlitwa nocna"
    assert body["order"] == 3


@pytest.mark.asyncio
async def test_update_service_time_can_explicitly_clear_description(ctx) -> None:
    client = ctx

    created = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "sobota", "time": "21:00", "description": "Modlitwa nocna"},
    )
    service_time_id = created.json()["id"]

    response = await client.patch(
        f"/api/congregations/{CHURCH_ID}/service-times/{service_time_id}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.asyncio
async def test_update_service_time_404_for_unknown_id(ctx) -> None:
    client = ctx

    response = await client.patch(
        f"/api/congregations/{CHURCH_ID}/service-times/does-not-exist",
        json={"day": "niedziela"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_service_time_404_for_wrong_tenant(ctx) -> None:
    client = ctx

    created = await client.post(
        f"/api/congregations/{CHURCH_ID}/service-times",
        json={"day": "sobota", "time": "21:00"},
    )
    service_time_id = created.json()["id"]

    response = await client.patch(
        f"/api/congregations/{OTHER_CHURCH_ID}/service-times/{service_time_id}",
        json={"day": "niedziela"},
    )

    assert response.status_code == 404
