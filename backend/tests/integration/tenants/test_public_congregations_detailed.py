"""Integration tests for GET /api/congregations/detailed."""

import os
from datetime import UTC, datetime, timedelta

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
from app.modules.auth.db_models import UserDB
from app.modules.churches.db_models import PersonDB, ServiceAssignmentDB, ServiceTypeDB
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.tenants.db_models import TenantDB
from main import app


async def _seed_public_congregation(session: AsyncSession) -> str:
    now = datetime.now(UTC)
    owner_id = generate_id()
    tenant_id = generate_id()
    pastor_type_id = generate_id()
    diacon_type_id = generate_id()

    session.add(
        UserDB(
            id=owner_id,
            email="owner@example.com",
            name="Owner",
            hashed_password="hash",
        )
    )
    session.add(
        TenantDB(
            id=tenant_id,
            name="Test Congregation",
            description="Test description",
            status="published",
            owner_id=owner_id,
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=tenant_id,
            city="Warszawa",
            street="Testowa 1",
            postal_code="00-001",
            status="published",
        )
    )
    session.add(
        ServiceTypeDB(
            id=pastor_type_id,
            slug="pastor",
            name="Pastor",
            scope_type="church",
            sort_order=10,
        )
    )
    session.add(
        ServiceTypeDB(
            id=diacon_type_id,
            slug="diacon",
            name="Diakon",
            scope_type="church",
            sort_order=20,
        )
    )

    pastor_person = PersonDB(
        id=generate_id(),
        first_name="Jan",
        last_name="Kowalski",
        phone="+48111111111",
        email="jan@example.com",
    )
    diacon_person = PersonDB(
        id=generate_id(),
        first_name="Anna",
        last_name="Nowak",
        phone="+48222222222",
        email="anna@example.com",
    )
    hidden_person = PersonDB(
        id=generate_id(),
        first_name="Hidden",
        last_name="Person",
        phone="+48333333333",
        email="hidden@example.com",
    )
    session.add_all([pastor_person, diacon_person, hidden_person])
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=diacon_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=tenant_id,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="authenticated",
            sort_order=1,
            created_at=now,
        )
    )
    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=pastor_person.id,
            service_type_id=pastor_type_id,
            scope_type="church",
            scope_id=tenant_id,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="public",
            sort_order=0,
            created_at=now + timedelta(seconds=1),
        )
    )
    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=hidden_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=tenant_id,
            card_visibility="hidden",
            phone_visibility="public",
            email_visibility="public",
            sort_order=2,
            created_at=now + timedelta(seconds=2),
        )
    )
    await session.commit()
    return tenant_id


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
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
        await _seed_public_congregation(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_congregations_detailed_returns_multiple_card_contacts(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/congregations/detailed")
    assert response.status_code == 200

    data = response.json()
    assert len(data["congregations"]) == 1

    congregation = data["congregations"][0]
    assert congregation["name"] == "Test Congregation"
    assert len(congregation["card_contacts"]) == 2

    assert congregation["card_contacts"][0]["name"] == "Jan Kowalski"
    assert congregation["card_contacts"][0]["title"] == "Pastor"
    assert congregation["card_contacts"][0]["phone"] == "+48111111111"
    assert congregation["card_contacts"][0]["email"] == "jan@example.com"

    assert congregation["card_contacts"][1]["name"] == "Anna Nowak"
    assert congregation["card_contacts"][1]["title"] == "Diakon"
    assert congregation["card_contacts"][1]["phone"] == "+48222222222"
    assert congregation["card_contacts"][1]["email"] is None

    assert congregation["contact_name"] == "Jan Kowalski"
    assert congregation["contact_title"] == "Pastor"
    assert congregation["contact_phone"] == "+48111111111"
    assert congregation["contact_email"] == "jan@example.com"


async def _seed_flipped_sort_order(session: AsyncSession) -> str:
    now = datetime.now(UTC)
    owner_id = generate_id()
    tenant_id = generate_id()
    pastor_type_id = generate_id()
    diacon_type_id = generate_id()

    session.add(
        UserDB(
            id=owner_id,
            email="owner-flip@example.com",
            name="Owner",
            hashed_password="hash",
        )
    )
    session.add(
        TenantDB(
            id=tenant_id,
            name="Flip Congregation",
            description="Test",
            status="published",
            owner_id=owner_id,
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=tenant_id,
            city="Kraków",
            street="Testowa 2",
            postal_code="30-001",
            status="published",
        )
    )
    session.add(
        ServiceTypeDB(
            id=pastor_type_id,
            slug="pastor",
            name="Pastor",
            scope_type="church",
            sort_order=10,
        )
    )
    session.add(
        ServiceTypeDB(
            id=diacon_type_id,
            slug="diacon",
            name="Diakon",
            scope_type="church",
            sort_order=20,
        )
    )

    pastor_person = PersonDB(
        id=generate_id(),
        first_name="Jan",
        last_name="Pastor",
        phone="+48111111111",
        email="jan@example.com",
    )
    diacon_person = PersonDB(
        id=generate_id(),
        first_name="Anna",
        last_name="Diacon",
        phone="+48222222222",
        email="anna@example.com",
    )
    session.add_all([pastor_person, diacon_person])
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=pastor_person.id,
            service_type_id=pastor_type_id,
            scope_type="church",
            scope_id=tenant_id,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="public",
            sort_order=1,
            created_at=now,
        )
    )
    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=diacon_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=tenant_id,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="public",
            sort_order=0,
            created_at=now + timedelta(seconds=1),
        )
    )
    await session.commit()
    return tenant_id


@pytest_asyncio.fixture
async def flipped_sort_client() -> AsyncClient:
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
        await _seed_flipped_sort_order(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_card_contacts_respect_manual_sort_order(
    flipped_sort_client: AsyncClient,
) -> None:
    response = await flipped_sort_client.get("/api/congregations/detailed")
    assert response.status_code == 200

    congregations = response.json()["congregations"]
    assert len(congregations) == 1
    names = [c["name"] for c in congregations[0]["card_contacts"]]
    assert names == ["Anna Diacon", "Jan Pastor"]
