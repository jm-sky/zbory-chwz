"""G12 — cache does not drift for the governance write path: grant a role via
POST /governance/role-assignments -> permission visible on the very next request,
revoke via DELETE -> permission gone on the very next request, with a *working*
cache (not PermissionCache(None), which every other test uses and which trivially
"passes" because there is nothing to invalidate). Mirrors
tests/unit/churches/test_permission_cache_invalidation.py (G0.1), but exercises the
governance-module grant/revoke path rather than the service-assignment one."""

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
from app.modules.churches.acl_seed import Permission, ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app


class FakeAsyncRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis (see
    test_permission_cache_invalidation.py) — exercises the same get/set/delete/incr
    surface PermissionCache uses, so invalidation is actually tested rather than
    short-circuited by cache=None."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        current = int(self._store.get(key, "0")) + 1
        self._store[key] = str(current)
        return current


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            UserDB(id="admin", email="admin@example.com", name="Admin"),
            UserDB(id="target", email="target@example.com", name="Target"),
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
    await ensure_acl_roles(session)
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

    cache = PermissionCache(FakeAsyncRedis())  # type: ignore[arg-type]

    def override_permission_service(db: AsyncSession = Depends(get_db)) -> PermissionService:
        return PermissionService(db, cache)

    app.dependency_overrides[get_permission_service] = override_permission_service

    async with session_factory() as session:
        world = await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user
            await client.get("/api/auth/csrf-token")

        yield client, login, world, session_factory, cache

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_grant_then_revoke_immediate_with_live_cache(ctx) -> None:
    client, login, world, session_factory, cache = ctx
    await login(_api_user("admin", is_admin=True))

    grant_response = await client.post(
        "/api/governance/role-assignments",
        json={
            "userId": "target",
            "roleName": "pastor",
            "scopeType": "church",
            "scopeId": world["church_id"],
        },
    )
    assert grant_response.status_code == 201, grant_response.text
    assignment_id = grant_response.json()["id"]

    async with session_factory() as session:
        next_request_service = PermissionService(session, cache)
        target = _api_user("target")
        assert await next_request_service.resolve(target, Permission.CHURCH_EDIT, ("church", world["church_id"]))

    revoke_response = await client.delete(f"/api/governance/role-assignments/{assignment_id}")
    assert revoke_response.status_code == 204

    async with session_factory() as session:
        post_revoke_service = PermissionService(session, cache)
        target = _api_user("target")
        assert not await post_revoke_service.resolve(target, Permission.CHURCH_EDIT, ("church", world["church_id"]))


@pytest.mark.asyncio
async def test_permission_exception_set_then_cleared_immediate_with_live_cache(ctx) -> None:
    client, login, world, session_factory, cache = ctx
    await login(_api_user("admin", is_admin=True))

    grant_response = await client.post(
        "/api/governance/role-assignments",
        json={
            "userId": "target",
            "roleName": "pastor",
            "scopeType": "church",
            "scopeId": world["church_id"],
        },
    )
    assert grant_response.status_code == 201, grant_response.text

    async with session_factory() as session:
        service = PermissionService(session, cache)
        target = _api_user("target")
        assert await service.resolve(target, Permission.CHURCH_PUBLISH, ("church", world["church_id"]))

    deny_response = await client.put(
        "/api/governance/user-permissions",
        json={
            "userId": "target",
            "scopeType": "church",
            "scopeId": world["church_id"],
            "permission": "church.publish",
            "effect": "deny",
        },
    )
    assert deny_response.status_code == 200, deny_response.text
    exception_id = deny_response.json()["id"]

    async with session_factory() as session:
        service = PermissionService(session, cache)
        target = _api_user("target")
        assert not await service.resolve(target, Permission.CHURCH_PUBLISH, ("church", world["church_id"]))

    clear_response = await client.delete(f"/api/governance/user-permissions/{exception_id}")
    assert clear_response.status_code == 204

    async with session_factory() as session:
        service = PermissionService(session, cache)
        target = _api_user("target")
        assert await service.resolve(target, Permission.CHURCH_PUBLISH, ("church", world["church_id"]))
