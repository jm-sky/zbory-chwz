"""G9 — user_permissions exception CRUD: subset rule extended to individual permissions
(can't set allow/deny for a permission you don't hold yourself); PUT is a true upsert
(one row survives repeated calls with different effects); DELETE restores the role-derived
permission; deny wins globally in the chain (§2)."""

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
from app.modules.churches.acl_models import UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            UserDB(id="bishop", email="bishop@example.com", name="Bishop"),
            UserDB(id="pastor", email="pastor@example.com", name="Pastor"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=None,
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
            UserRoleAssignmentDB(id=generate_id(), user_id="bishop", role_id=roles["bishop"].id, scope_type="community", scope_id=community_id),
            UserRoleAssignmentDB(id=generate_id(), user_id="pastor", role_id=roles["pastor"].id, scope_type="church", scope_id=church_id),
        ]
    )
    await session.commit()

    return {"community_id": community_id, "church_id": church_id}


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

        yield client, login, world, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_deny_on_community_blocks_pastor_in_church(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("bishop"))

    response = await client.put(
        "/api/governance/user-permissions",
        json={
            "userId": "pastor",
            "scopeType": "community",
            "scopeId": world["community_id"],
            "permission": "church.edit",
            "effect": "deny",
        },
    )
    assert response.status_code == 200, response.text

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        pastor = _api_user("pastor")
        assert not await permission_service.resolve(pastor, "church.edit", ("church", world["church_id"]))


@pytest.mark.asyncio
async def test_cannot_set_exception_for_permission_you_do_not_hold(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("pastor"))

    response = await client.put(
        "/api/governance/user-permissions",
        json={
            "userId": "bishop",
            "scopeType": "church",
            "scopeId": world["church_id"],
            "permission": "church.publish",
            "effect": "allow",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_put_twice_with_different_effect_upserts_one_row(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("bishop"))

    payload = {
        "userId": "pastor",
        "scopeType": "church",
        "scopeId": world["church_id"],
        "permission": "church.move_region",
        "effect": "allow",
    }
    first = await client.put("/api/governance/user-permissions", json=payload)
    assert first.status_code == 200, first.text

    second = await client.put("/api/governance/user-permissions", json={**payload, "effect": "deny"})
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["effect"] == "deny"

    async with session_factory() as session:
        from sqlalchemy import select

        rows = (
            (
                await session.execute(
                    select(UserPermissionDB).where(
                        UserPermissionDB.user_id == "pastor",
                        UserPermissionDB.permission == "church.move_region",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].effect == "deny"


@pytest.mark.asyncio
async def test_delete_restores_role_derived_permission(ctx) -> None:
    client, login, world, session_factory = ctx
    await login(_api_user("bishop"))

    create_response = await client.put(
        "/api/governance/user-permissions",
        json={
            "userId": "pastor",
            "scopeType": "church",
            "scopeId": world["church_id"],
            "permission": "church.edit",
            "effect": "deny",
        },
    )
    assert create_response.status_code == 200
    exception_id = create_response.json()["id"]

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        pastor = _api_user("pastor")
        assert not await permission_service.resolve(pastor, "church.edit", ("church", world["church_id"]))

    delete_response = await client.delete(f"/api/governance/user-permissions/{exception_id}")
    assert delete_response.status_code == 204

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        pastor = _api_user("pastor")
        assert await permission_service.resolve(pastor, "church.edit", ("church", world["church_id"]))
