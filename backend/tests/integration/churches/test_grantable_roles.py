"""G0.4 — GET /churches/grantable-roles must return exactly the roles the caller could
successfully grant via the write path (assert_can_grant_role / can_grant_role share one
source of truth in acl_grant_rules._grant_role_denial_reason)."""

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
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.db_models import ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from fastapi import Depends
from main import app


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            UserDB(id="pastor", email="pastor@example.com", name="Pastor"),
            UserDB(id="rb", email="rb@example.com", name="RB"),
            UserDB(id="admin", email="admin@example.com", name="Admin"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(id=region_id, community_id=community_id, name="Centralny", slug="centralny", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=region_id,
                tenant_id=church_id,
                name="Warszawa",
                visibility="public",
                created_at=now,
            ),
        ]
    )
    await session.flush()
    roles = await ensure_acl_roles(session)
    session.add_all(
        [
            UserRoleAssignmentDB(id=generate_id(), user_id="pastor", role_id=roles["pastor"].id, scope_type="church", scope_id=church_id),
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id="rb",
                role_id=roles["regional_bishop"].id,
                scope_type="region",
                scope_id=region_id,
            ),
        ]
    )
    await session.commit()
    return {"community_id": community_id, "region_id": region_id, "church_id": church_id}


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

    def override_permission_service(db: AsyncSession = Depends(get_db)) -> PermissionService:
        return PermissionService(db, PermissionCache(None))

    app.dependency_overrides[get_permission_service] = override_permission_service

    async with session_factory() as session:
        world = await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, login, world

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pastor_without_services_manage_gets_no_grantable_roles(ctx) -> None:
    client, login, world = ctx
    login(_api_user("pastor"))

    response = await client.get(
        "/api/churches/grantable-roles",
        params={"scopeType": "church", "scopeId": world["church_id"]},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_regional_bishop_can_grant_church_scoped_roles_in_own_region(ctx) -> None:
    client, login, world = ctx
    login(_api_user("rb"))

    response = await client.get(
        "/api/churches/grantable-roles",
        params={"scopeType": "church", "scopeId": world["church_id"]},
    )
    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert names == {"pastor", "diacon"}


@pytest.mark.asyncio
async def test_regional_bishop_cannot_grant_bishop_role(ctx) -> None:
    client, login, world = ctx
    login(_api_user("rb"))

    response = await client.get(
        "/api/churches/grantable-roles",
        params={"scopeType": "community", "scopeId": world["community_id"]},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_admin_can_grant_bishop_role(ctx) -> None:
    client, login, world = ctx
    login(_api_user("admin", is_admin=True))

    response = await client.get(
        "/api/churches/grantable-roles",
        params={"scopeType": "community", "scopeId": world["community_id"]},
    )
    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert names == {"bishop"}


@pytest.mark.asyncio
async def test_unknown_scope_is_404(ctx) -> None:
    client, login, world = ctx
    login(_api_user("admin", is_admin=True))

    response = await client.get(
        "/api/churches/grantable-roles",
        params={"scopeType": "church", "scopeId": "does-not-exist"},
    )
    assert response.status_code == 404
