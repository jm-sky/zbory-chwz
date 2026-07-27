"""G0.1 — cache invalidation must make ACL changes visible immediately, even with a working
Redis-like cache (not PermissionCache(None), which every other test uses and which trivially
"passes" because there is nothing to invalidate)."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.auth.db_models import UserDB
from app.modules.auth.models import User
from app.modules.churches.acl_seed import Permission
from app.modules.churches.db_models import ChurchDB, CommunityDB, ServiceTypeDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import ServiceAssignmentCreateRequest


class FakeAsyncRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis, exercising the same
    get/set/delete/incr surface PermissionCache uses, so invalidation is actually tested
    rather than short-circuited by cache=None."""

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


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db

    await engine.dispose()


def _admin() -> User:
    return User(
        id="admin",
        email="admin@example.com",
        name="Admin",
        isAdmin=True,
        createdAt=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_role_grant_and_revoke_visible_immediately_with_live_cache(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=None,
                tenant_id=church_id,
                name="Zbor",
                visibility="hidden",
                created_at=now,
            ),
            ServiceTypeDB(
                id=generate_id(),
                slug="diacon-test",
                name="Diakon",
                scope_type="church",
                suggested_role="diacon",
                sort_order=0,
                created_at=now,
            ),
        ]
    )
    await session.flush()
    service_type = (await session.execute(select(ServiceTypeDB))).scalar_one()
    service_type_id = service_type.id

    admin = _admin()
    cache = PermissionCache(FakeAsyncRedis())  # type: ignore[arg-type]
    repo = ChurchRepository(session)

    payload = ServiceAssignmentCreateRequest(
        firstName="Jan",
        lastName="Kowalski",
        email="jan.kowalski@example.com",
        serviceTypeId=service_type_id,
        createAccount=True,
        suggestedRole="diacon",
    )

    permission_service = PermissionService(session, cache)
    assignment = await repo.create_service_assignment(
        "church",
        church_id,
        payload,
        actor=admin,
        permission_service=permission_service,
    )

    target_user = (await session.execute(select(UserDB).where(UserDB.email == "jan.kowalski@example.com"))).scalar_one_or_none()
    assert target_user is not None
    target = User(id=target_user.id, email=target_user.email, name=target_user.name, createdAt=now)

    # Next request builds a fresh PermissionService sharing the same (Redis-backed) cache.
    next_request_service = PermissionService(session, cache)
    assert await next_request_service.resolve(target, Permission.PEOPLE_MANAGE, ("church", church_id))

    delete_request_service = PermissionService(session, cache)
    deleted = await repo.delete_service_assignment("church", church_id, assignment.id, cache=delete_request_service.cache)
    assert deleted

    post_delete_service = PermissionService(session, cache)
    assert not await post_delete_service.resolve(target, Permission.PEOPLE_MANAGE, ("church", church_id))
