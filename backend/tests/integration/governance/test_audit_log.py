"""G11 — audit log read API: services.manage gate (admin/owner bypass), batch grouping,
pagination/total, and that the log has no write endpoint (append-only, G8)."""

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
            UserDB(id="bishop1", email="bishop1@example.com", name="Bishop One"),
            UserDB(id="pastor", email="pastor@example.com", name="Pastor"),
            UserDB(id="target", email="target@example.com", name="Target User"),
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
                scope_id=church_other_region_id,
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
            await client.get("/api/auth/csrf-token")

        yield client, login, world

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_grant_is_visible_in_audit_log(ctx) -> None:
    client, login, world = ctx
    await login(_api_user("rb"))

    grant = await client.post(
        "/api/governance/role-assignments",
        json={"userId": "target", "roleName": "pastor", "scopeType": "church", "scopeId": world["church_id"]},
    )
    assert grant.status_code == 201, grant.text

    response = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert len(body["batches"]) == 1
    batch = body["batches"][0]
    assert batch["actorLabel"] == "rb"
    entry = batch["entries"][0]
    assert entry["action"] == "role.grant"
    assert entry["roleName"] == "pastor"
    assert entry["targetLabel"] == "Target User"


@pytest.mark.asyncio
async def test_pastor_without_services_manage_gets_403_even_in_own_church(ctx) -> None:
    """`pastor` deliberately lacks services.manage (acl_seed.py) — holding a role in a
    scope does not by itself grant audit-log read access there."""
    client, login, world = ctx
    await login(_api_user("pastor"))

    response = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_other_region_id"]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bishop_can_read_audit_log_for_any_church_in_their_community(ctx) -> None:
    client, login, world = ctx
    await login(_api_user("bishop1"))

    response = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_other_region_id"]},
    )
    assert response.status_code == 200
    assert response.json() == {"batches": [], "total": 0}


@pytest.mark.asyncio
async def test_admin_bypasses_scope_gate(ctx) -> None:
    client, login, world = ctx
    await login(_api_user("admin", is_admin=True))

    response = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_id"]},
    )
    assert response.status_code == 200
    assert response.json() == {"batches": [], "total": 0}


@pytest.mark.asyncio
async def test_pagination_and_total_across_multiple_batches(ctx) -> None:
    client, login, world = ctx
    await login(_api_user("rb"))

    for role in ("pastor", "diacon"):
        response = await client.post(
            "/api/governance/role-assignments",
            json={"userId": "target", "roleName": role, "scopeType": "church", "scopeId": world["church_id"]},
        )
        assert response.status_code == 201, response.text

    first_page = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_id"], "skip": 0, "limit": 1},
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert len(first_page.json()["batches"]) == 1

    second_page = await client.get(
        "/api/governance/audit-log",
        params={"scopeType": "church", "scopeId": world["church_id"], "skip": 1, "limit": 1},
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["batches"]) == 1
    assert first_page.json()["batches"][0]["batchId"] != second_page.json()["batches"][0]["batchId"]


@pytest.mark.asyncio
async def test_audit_log_has_no_write_endpoint(ctx) -> None:
    client, login, world = ctx
    await login(_api_user("admin", is_admin=True))

    for method in ("post", "put", "patch", "delete"):
        response = await client.request(method, "/api/governance/audit-log")
        assert response.status_code == 405
