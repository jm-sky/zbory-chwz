"""Tests for POST /admin/congregations/import/apply."""

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
from app.modules.churches.db_models import ChurchDB, PersonDB, ServiceAssignmentDB, ServiceTypeDB
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.tenants.db_models import TenantDB
from main import app

ADMIN_ID = "user-admin"
MEMBER_ID = "user-member"
EXISTING_TENANT_ID = "tenant-warszawa"
DIACON_SERVICE_TYPE_ID = "service-type-diakon"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add(
        TenantDB(
            id=EXISTING_TENANT_ID,
            name="ZBÓR W WARSZAWIE",
            status="published",
            owner_id=MEMBER_ID,
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=EXISTING_TENANT_ID,
            street="Stara 1",
            city="Warszawa",
            postal_code="00-001",
            country="PL",
            status="published",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        ServiceTypeDB(
            id=DIACON_SERVICE_TYPE_ID,
            slug="diakon",
            name="Diakon",
            scope_type="church",
            suggested_role="diacon",
            is_senior_tier=False,
            sort_order=70,
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
async def test_apply_updates_existing_congregation_address(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={
            "items": [
                {
                    "action": "update",
                    "tenant_id": EXISTING_TENANT_ID,
                    "fields": [
                        {"field": "street", "value": "Nowa 5", "apply": True},
                        {"field": "postal_code", "value": "00-999", "apply": False},
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"created": 0, "updated": 1, "skipped": 0}

    async with session_factory() as session:
        result = await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == EXISTING_TENANT_ID))
        address = result.scalar_one()
        assert address.street == "Nowa 5"
        # apply: False fields must be left untouched
        assert address.postal_code == "00-001"


@pytest.mark.asyncio
async def test_apply_creates_new_congregation(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={
            "items": [
                {
                    "action": "create",
                    "congregation_name": "ZBÓR W KRAKOWIE",
                    "fields": [
                        {"field": "city", "value": "Kraków", "apply": True},
                        {"field": "country", "value": "PL", "apply": True},
                        {
                            "field": "contact_name",
                            "value": "Jan Kowalski",
                            "apply": True,
                        },
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"created": 1, "updated": 0, "skipped": 0}

    async with session_factory() as session:
        tenant = await session.scalar(select(TenantDB).where(TenantDB.name == "ZBÓR W KRAKOWIE"))
        assert tenant is not None
        church = await session.scalar(select(ChurchDB).where(ChurchDB.id == tenant.id))
        assert church is not None
        address = await session.scalar(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == tenant.id))
        assert address is not None
        assert address.city == "Kraków"
        assignment = await session.scalar(
            select(ServiceAssignmentDB).where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id == tenant.id,
            )
        )
        assert assignment is not None
        person = await session.scalar(select(PersonDB).where(PersonDB.id == assignment.person_id))
        assert person is not None
        assert person.first_name == "Jan"
        assert person.last_name == "Kowalski"


@pytest.mark.asyncio
async def test_apply_creating_new_congregation_without_city_fails(ctx) -> None:
    client, login, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={
            "items": [
                {
                    "action": "create",
                    "congregation_name": "ZBÓR BEZ ADRESU",
                    "fields": [
                        {"field": "street", "value": "Jakaś 1", "apply": True},
                    ],
                }
            ]
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_apply_skip_item_makes_no_changes(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={"items": [{"action": "skip", "fields": []}]},
    )

    assert response.status_code == 200
    assert response.json() == {"created": 0, "updated": 0, "skipped": 1}

    async with session_factory() as session:
        result = await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == EXISTING_TENANT_ID))
        address = result.scalar_one()
        assert address.street == "Stara 1"


@pytest.mark.asyncio
async def test_apply_updates_only_the_pinned_contact_when_multiple_exist(ctx) -> None:
    """With two contacts on a congregation, applying must edit the one the
    analyze step matched by name - not silently overwrite whichever one
    happens to come first."""
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    now = datetime.now(UTC)
    jan_person_id = generate_id()
    marek_person_id = generate_id()
    jan_assignment_id = generate_id()
    marek_assignment_id = generate_id()
    async with session_factory() as session:
        session.add(
            PersonDB(
                id=jan_person_id,
                first_name="Jan",
                last_name="Madeyski",
                phone="+48668292049",
            )
        )
        session.add(
            PersonDB(
                id=marek_person_id,
                first_name="Marek",
                last_name="Kowalski",
                phone="+48111222333",
            )
        )
        session.add(
            ServiceAssignmentDB(
                id=jan_assignment_id,
                person_id=jan_person_id,
                service_type_id=DIACON_SERVICE_TYPE_ID,
                scope_type="church",
                scope_id=EXISTING_TENANT_ID,
                show_on_list=True,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                sort_order=0,
                created_at=now,
            )
        )
        session.add(
            ServiceAssignmentDB(
                id=marek_assignment_id,
                person_id=marek_person_id,
                service_type_id=DIACON_SERVICE_TYPE_ID,
                scope_type="church",
                scope_id=EXISTING_TENANT_ID,
                show_on_list=True,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                sort_order=1,
                created_at=now,
            )
        )
        await session.commit()

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={
            "items": [
                {
                    "action": "update",
                    "tenant_id": EXISTING_TENANT_ID,
                    "contact_person_id": jan_assignment_id,
                    "fields": [
                        {"field": "contact_phone", "value": "+48600700800", "apply": True},
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"created": 0, "updated": 1, "skipped": 0}

    async with session_factory() as session:
        jan = await session.get(PersonDB, jan_person_id)
        marek = await session.get(PersonDB, marek_person_id)
        assert jan is not None
        assert marek is not None
        assert jan.phone == "+48600700800"
        # The other deacon must be untouched.
        assert marek.phone == "+48111222333"


@pytest.mark.asyncio
async def test_apply_requires_admin(ctx) -> None:
    client, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        "/api/admin/congregations/import/apply",
        json={"items": [{"action": "skip", "fields": []}]},
    )

    assert response.status_code == 403
