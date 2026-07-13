"""Tests for GET /congregations/{tenant_id}/change-log access control and content.

See docs/plans/2026-07-13--clergy-email-updates.md.
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

from app.common.id_utils import generate_id
from app.core.database import Base, get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import RoleDB, UserRoleAssignmentDB
from app.modules.churches.db_models import ChurchDB, CommunityDB
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

ADMIN_ID = "user-admin"
OWNER_MEMBER_ID = "user-owner-member"
BISHOP_ID = "user-bishop"
STRANGER_ID = "user-stranger"
TENANT_ID = "tenant-swiebodzin"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add(TenantDB(id=TENANT_ID, name="Zbór w Świebodzinie", status="published", owner_id=OWNER_MEMBER_ID, created_at=now))
    community = CommunityDB(id=generate_id(), name="CHWZ", slug="chwz", visibility="hidden")
    session.add(community)
    await session.flush()
    session.add(ChurchDB(id=TENANT_ID, community_id=community.id, region_id=None, tenant_id=OWNER_MEMBER_ID, name="Zbór w Świebodzinie"))
    session.add(TenantMembershipDB(tenant_id=TENANT_ID, user_id=OWNER_MEMBER_ID, role="owner"))

    role = RoleDB(id=generate_id(), name="bishop", scope_type="community")
    session.add(role)
    await session.flush()
    session.add(UserRoleAssignmentDB(id=generate_id(), user_id=BISHOP_ID, role_id=role.id, scope_type="community", scope_id=community.id))

    session.add(
        CongregationChangeLogDB(
            id=generate_id(),
            tenant_id=TENANT_ID,
            section="contact",
            field="contact_phone",
            old_value=None,
            new_value="+48600111222",
            source="email_auto",
            actor_label="Jan Kowalski (automatycznie, AI 0.95)",
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

        yield client, login

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_can_view_change_log(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get(f"/api/congregations/{TENANT_ID}/change-log")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["field"] == "contact_phone"
    assert entries[0]["field_label"] == "Telefon"
    assert entries[0]["actor_label"] == "Jan Kowalski (automatycznie, AI 0.95)"


@pytest.mark.asyncio
async def test_tenant_member_can_view_change_log(ctx) -> None:
    client, login = ctx
    login(_api_user(OWNER_MEMBER_ID))

    response = await client.get(f"/api/congregations/{TENANT_ID}/change-log")

    assert response.status_code == 200
    assert len(response.json()["entries"]) == 1


@pytest.mark.asyncio
async def test_pastoral_acl_user_can_view_change_log(ctx) -> None:
    """A community-scope bishop with no direct tenant membership - only ACL access."""
    client, login = ctx
    login(_api_user(BISHOP_ID))

    response = await client.get(f"/api/congregations/{TENANT_ID}/change-log")

    assert response.status_code == 200
    assert len(response.json()["entries"]) == 1


@pytest.mark.asyncio
async def test_unrelated_user_cannot_view_change_log(ctx) -> None:
    client, login = ctx
    login(_api_user(STRANGER_ID))

    response = await client.get(f"/api/congregations/{TENANT_ID}/change-log")

    assert response.status_code == 403
