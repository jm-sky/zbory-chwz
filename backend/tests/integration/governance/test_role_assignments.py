"""G5 — governance role-assignment CRUD: subset rule, elevated-role gate, cache
consistency, exclusion-of-self guard, and the "delete the assignment instead" 409 for
grants that came from a service assignment."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi import Depends
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
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_central_id = generate_id()
    region_other_id = generate_id()
    church_id = generate_id()
    church_other_region_id = generate_id()

    session.add_all(
        [
            UserDB(id="rb", email="rb@example.com", name="RB"),
            UserDB(id="target", email="target@example.com", name="Target User"),
            UserDB(id="pastor", email="pastor@example.com", name="Pastor"),
            UserDB(id="bishop1", email="bishop1@example.com", name="Bishop One"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(id=region_central_id, community_id=community_id, name="Centralny", slug="centralny", created_at=now),
            RegionDB(id=region_other_id, community_id=community_id, name="Inny", slug="inny", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=region_central_id,
                tenant_id=church_id,
                name="Warszawa",
                visibility="public",
                created_at=now,
            ),
            ChurchDB(
                id=church_other_region_id,
                community_id=community_id,
                region_id=region_other_id,
                tenant_id=church_other_region_id,
                name="Zabrze",
                visibility="public",
                created_at=now,
            ),
        ]
    )
    await session.flush()

    roles = await ensure_acl_roles(session)
    service_source_id = generate_id()
    session.add_all(
        [
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id="rb",
                role_id=roles["regional_bishop"].id,
                scope_type="region",
                scope_id=region_central_id,
            ),
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id="bishop1",
                role_id=roles["bishop"].id,
                scope_type="community",
                scope_id=community_id,
            ),
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id="pastor",
                role_id=roles["pastor"].id,
                scope_type="church",
                scope_id=church_id,
                source_assignment_id=service_source_id,
            ),
        ]
    )
    await session.commit()

    return {
        "community_id": community_id,
        "region_central_id": region_central_id,
        "region_other_id": region_other_id,
        "church_id": church_id,
        "church_other_region_id": church_other_region_id,
    }


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

        async def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user
            # Belt-and-suspenders: the autouse CSRF-injection fixture
            # (tests/integration/conftest.py) covers most cases, but explicitly seeding
            # the cookie here matches the established pattern in test_permission_matrix.py
            # and avoids flakiness when many integration files run in one session.
            await client.get("/api/auth/csrf-token")

        yield client, login, world, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_regional_bishop_grants_pastor_in_own_region(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("rb"))

    response = await client.post(
        "/api/governance/role-assignments",
        json={"userId": "target", "roleName": "pastor", "scopeType": "church", "scopeId": world["church_id"]},
    )
    assert response.status_code == 201, response.text
    assert response.json()["roleName"] == "pastor"


@pytest.mark.asyncio
async def test_regional_bishop_cannot_grant_in_other_region(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("rb"))

    response = await client.post(
        "/api/governance/role-assignments",
        json={
            "userId": "target",
            "roleName": "pastor",
            "scopeType": "church",
            "scopeId": world["church_other_region_id"],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_only_admin_or_community_services_manage_grants_bishop(ctx) -> None:
    client, login, world, session_factory = ctx

    await login(_api_user("rb"))
    denied = await client.post(
        "/api/governance/role-assignments",
        json={"userId": "target", "roleName": "bishop", "scopeType": "community", "scopeId": world["community_id"]},
    )
    assert denied.status_code == 403

    await login(_api_user("admin", is_admin=True))
    allowed = await client.post(
        "/api/governance/role-assignments",
        json={"userId": "target", "roleName": "bishop", "scopeType": "community", "scopeId": world["community_id"]},
    )
    assert allowed.status_code == 201, allowed.text


@pytest.mark.asyncio
async def test_cannot_delete_grant_from_service_assignment(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("admin", is_admin=True))

    async with session_factory() as session:
        from sqlalchemy import select

        row = (await session.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.user_id == "pastor"))).scalars().first()
        assignment_id = row.id

    response = await client.delete(f"/api/governance/role-assignments/{assignment_id}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cannot_delete_last_bishop_in_community(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("admin", is_admin=True))

    async with session_factory() as session:
        from sqlalchemy import select

        row = (await session.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.user_id == "bishop1"))).scalars().first()
        assignment_id = row.id

    response = await client.delete(f"/api/governance/role-assignments/{assignment_id}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_grant_then_revoke_updates_access_immediately(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("rb"))

    create_response = await client.post(
        "/api/governance/role-assignments",
        json={"userId": "target", "roleName": "pastor", "scopeType": "church", "scopeId": world["church_id"]},
    )
    assert create_response.status_code == 201
    assignment_id = create_response.json()["id"]

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        target = _api_user("target")
        assert await permission_service.resolve(target, "church.edit", ("church", world["church_id"]))

    delete_response = await client.delete(f"/api/governance/role-assignments/{assignment_id}")
    assert delete_response.status_code == 204

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        target = _api_user("target")
        assert not await permission_service.resolve(target, "church.edit", ("church", world["church_id"]))
