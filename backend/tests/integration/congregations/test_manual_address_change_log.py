"""Tests that manually editing a congregation's address (POST/PATCH
/congregations/{tenant_id}/address) writes admin_manual change-log rows —
previously only the clergy e-mail pipeline ever wrote to
congregation_change_log, so a plain form edit left no trace.
"""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB
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
async def test_create_address_logs_admin_manual_entries(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(OWNER_ID))

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/address",
        json={"city": "Poznań", "street": "Rynek 1", "country": "PL", "status": "draft"},
    )

    assert response.status_code == 201

    async with session_factory() as session:
        result = await session.execute(select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == TENANT_ID))
        entries = {entry.field: entry for entry in result.scalars().all()}

    assert entries["city"].old_value is None
    assert entries["city"].new_value == "Poznań"
    assert entries["city"].section == "address"
    assert entries["city"].source == "admin_manual"
    assert entries["city"].actor_label == OWNER_ID
    assert entries["street"].new_value == "Rynek 1"


@pytest.mark.asyncio
async def test_update_address_logs_only_changed_fields(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(OWNER_ID))

    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=TENANT_ID,
                street="Stara 1",
                city="Poznań",
                country="PL",
                status="draft",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    response = await client.patch(
        f"/api/congregations/{TENANT_ID}/address",
        json={"street": "Nowa 2"},
    )

    assert response.status_code == 200

    async with session_factory() as session:
        result = await session.execute(select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == TENANT_ID))
        entries = list(result.scalars().all())

    assert len(entries) == 1
    assert entries[0].field == "street"
    assert entries[0].old_value == "Stara 1"
    assert entries[0].new_value == "Nowa 2"
    assert entries[0].source == "admin_manual"


@pytest.mark.asyncio
async def test_update_address_with_coordinates_marks_manual_and_logs_them(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(OWNER_ID))

    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=TENANT_ID,
                street="Stara 1",
                city="Poznań",
                country="PL",
                status="draft",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    response = await client.patch(
        f"/api/congregations/{TENANT_ID}/address",
        json={"latitude": 52.4064, "longitude": 16.9252},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["latitude"] == pytest.approx(52.4064)
    assert body["longitude"] == pytest.approx(16.9252)
    assert body["geocode_status"] == "manual"

    async with session_factory() as session:
        result = await session.execute(select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == TENANT_ID))
        entries = {entry.field: entry for entry in result.scalars().all()}

    assert entries["latitude"].old_value is None
    assert entries["latitude"].new_value == "52.4064"
    assert entries["longitude"].new_value == "16.9252"


@pytest.mark.asyncio
async def test_update_address_no_changes_logs_nothing(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(OWNER_ID))

    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=TENANT_ID,
                street="Stara 1",
                city="Poznań",
                country="PL",
                status="draft",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    response = await client.patch(f"/api/congregations/{TENANT_ID}/address", json={"street": "Stara 1"})

    assert response.status_code == 200

    async with session_factory() as session:
        result = await session.execute(select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == TENANT_ID))
        entries = list(result.scalars().all())

    assert entries == []
