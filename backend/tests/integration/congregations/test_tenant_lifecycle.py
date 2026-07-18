"""Admin congregation lifecycle: create, soft delete, restore.

Regression cover for:
- hard DELETE violated the tenant_memberships FK and cascaded churches away
- a tenant created at runtime had no `churches` row, so the edit page 404'd
- BranchResponse/ChurchResponse/RegionResponse/PersonResponse were built by
  field name while declaring `validation_alias`, raising ValidationError (500)
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
from app.modules.churches.db_models import ChurchDB
from app.modules.tenants.db_models import TenantDB
from main import app

OWNER_ID = "user-owner"


def _owner() -> User:
    return User(
        id=OWNER_ID,
        email="owner@example.com",
        name="Owner",
        isAdmin=False,
        isOwner=True,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> None:
    session.add(UserDB(id=OWNER_ID, email="owner@example.com", name="Owner"))
    await session.commit()


@pytest_asyncio.fixture
async def client():
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
    app.dependency_overrides[get_current_user] = _owner

    async with session_factory() as session:
        await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _create_tenant(c: AsyncClient, name: str = "Nowy Zbór") -> str:
    response = await c.post("/api/admin/tenants", json={"name": name, "status": "draft"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_owner_can_create_congregation(client) -> None:
    c, _ = client

    tenant_id = await _create_tenant(c)

    listing = await c.get("/api/admin/tenants")
    assert any(t["id"] == tenant_id for t in listing.json()["tenants"])


@pytest.mark.asyncio
async def test_created_congregation_gets_a_church_row(client) -> None:
    c, session_factory = client

    tenant_id = await _create_tenant(c)

    async with session_factory() as session:
        assert await session.get(ChurchDB, tenant_id) is not None

    # The edit page's church-backed sections must work straight away.
    assert (await c.get(f"/api/churches/{tenant_id}/branches")).status_code == 200
    assert (await c.get(f"/api/churches/{tenant_id}/service-assignments")).status_code == 200


@pytest.mark.asyncio
async def test_branch_crud_serializes(client) -> None:
    c, _ = client
    tenant_id = await _create_tenant(c)

    created = await c.post(f"/api/churches/{tenant_id}/branches", json={"name": "Placówka Praga"})
    assert created.status_code == 201, created.text
    branch = created.json()
    assert branch["churchId"] == tenant_id
    assert branch["slug"] == "placowka-praga"

    listed = await c.get(f"/api/churches/{tenant_id}/branches")
    assert listed.status_code == 200
    assert listed.json()[0]["churchId"] == tenant_id

    church = await c.get(f"/api/churches/{tenant_id}")
    assert church.status_code == 200
    assert church.json()["tenantId"]


@pytest.mark.asyncio
async def test_delete_is_soft_and_keeps_the_church(client) -> None:
    c, session_factory = client
    tenant_id = await _create_tenant(c)

    response = await c.delete(f"/api/admin/tenants/{tenant_id}")
    assert response.status_code == 204

    async with session_factory() as session:
        tenant = await session.get(TenantDB, tenant_id)
        assert tenant is not None
        assert tenant.deleted_at is not None
        assert tenant.status == "draft"
        assert await session.get(ChurchDB, tenant_id) is not None

    listing = await c.get("/api/admin/tenants")
    assert not any(t["id"] == tenant_id for t in listing.json()["tenants"])

    with_deleted = await c.get("/api/admin/tenants", params={"include_deleted": True})
    row = next(t for t in with_deleted.json()["tenants"] if t["id"] == tenant_id)
    assert row["deletedAt"] is not None


@pytest.mark.asyncio
async def test_deleted_congregation_is_unreachable(client) -> None:
    c, _ = client
    tenant_id = await _create_tenant(c)
    await c.delete(f"/api/admin/tenants/{tenant_id}")

    assert (await c.get(f"/api/congregations/{tenant_id}/address")).status_code == 404

    public = await c.get("/api/congregations/detailed")
    assert not any(t["id"] == tenant_id for t in public.json()["congregations"])


@pytest.mark.asyncio
async def test_restore_brings_the_congregation_back(client) -> None:
    c, _ = client
    tenant_id = await _create_tenant(c)
    await c.delete(f"/api/admin/tenants/{tenant_id}")

    restored = await c.post(f"/api/admin/tenants/{tenant_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["deletedAt"] is None

    listing = await c.get("/api/admin/tenants")
    assert any(t["id"] == tenant_id for t in listing.json()["tenants"])


@pytest.mark.asyncio
async def test_admin_tenants_listing_includes_completeness_inputs(client) -> None:
    """The admin tenant listing must carry enough data (address, service times,
    contact count) for the frontend to compute a profile completeness score."""
    c, _ = client

    bare_id = await _create_tenant(c, name="Zbór bez danych")

    filled_id = await _create_tenant(c, name="Zbór wypełniony")
    address_response = await c.post(
        f"/api/congregations/{filled_id}/address",
        json={"street": "ul. Kwiatowa 1", "city": "Warszawa", "postal_code": "00-001"},
    )
    assert address_response.status_code == 201, address_response.text

    service_time_response = await c.post(
        f"/api/congregations/{filled_id}/service-times",
        json={"day": "niedziela", "time": "10:00"},
    )
    assert service_time_response.status_code == 201, service_time_response.text

    assignment_response = await c.post(
        f"/api/churches/{filled_id}/service-assignments",
        json={"firstName": "Jan", "lastName": "Kowalski", "customServiceName": "Pastor"},
    )
    assert assignment_response.status_code == 201, assignment_response.text

    listing = await c.get("/api/admin/tenants")
    tenants_by_id = {t["id"]: t for t in listing.json()["tenants"]}

    bare = tenants_by_id[bare_id]
    assert bare["street"] is None
    assert bare["service_times_count"] == 0
    assert bare["card_contacts_count"] == 0

    filled = tenants_by_id[filled_id]
    assert filled["street"] == "ul. Kwiatowa 1"
    assert filled["city"] == "Warszawa"
    assert filled["service_times_count"] == 1
    assert filled["card_contacts_count"] == 1
