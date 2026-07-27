"""G0.3 — per-church effective permissions in permissions_for_user, computed in one query
regardless of how many churches exist (no more N calls to resolve() per church)."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission, ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db

    await engine.dispose()


def _user(user_id: str = "u1") -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, createdAt=datetime.now(UTC))


async def _seed_world(session: AsyncSession, *, n_churches_outside_region: int) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_id = generate_id()
    other_region_id = generate_id()
    church_in_region_id = generate_id()

    session.add_all(
        [
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(id=region_id, community_id=community_id, name="Centralny", slug="centralny", created_at=now),
            RegionDB(id=other_region_id, community_id=community_id, name="Inny", slug="inny", created_at=now),
            ChurchDB(
                id=church_in_region_id,
                community_id=community_id,
                region_id=region_id,
                tenant_id=church_in_region_id,
                name="Warszawa",
                visibility="public",
                created_at=now,
            ),
        ]
    )
    for _ in range(n_churches_outside_region):
        cid = generate_id()
        session.add(
            ChurchDB(
                id=cid,
                community_id=community_id,
                region_id=other_region_id,
                tenant_id=cid,
                name="Poza rejonem",
                visibility="public",
                created_at=now,
            )
        )
    await session.flush()
    return {"community_id": community_id, "region_id": region_id, "church_in_region_id": church_in_region_id}


@pytest.mark.asyncio
async def test_regional_bishop_sees_only_churches_in_own_region(session: AsyncSession) -> None:
    world = await _seed_world(session, n_churches_outside_region=3)
    roles = await ensure_acl_roles(session)
    bishop = _user("rb")
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=bishop.id,
            role_id=roles["regional_bishop"].id,
            scope_type="region",
            scope_id=world["region_id"],
        )
    )
    await session.commit()

    service = PermissionService(session, PermissionCache(None))
    payload = await service.permissions_for_user(bishop)

    church_ids = {c["churchId"] for c in payload["churches"]}
    assert church_ids == {world["church_in_region_id"]}
    in_region = next(c for c in payload["churches"] if c["churchId"] == world["church_in_region_id"])
    assert Permission.CHURCH_EDIT in in_region["permissions"]


@pytest.mark.asyncio
async def test_query_count_does_not_grow_with_church_count(session: AsyncSession) -> None:
    world = await _seed_world(session, n_churches_outside_region=1)
    roles = await ensure_acl_roles(session)
    bishop = _user("rb")
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=bishop.id,
            role_id=roles["regional_bishop"].id,
            scope_type="region",
            scope_id=world["region_id"],
        )
    )
    await session.commit()

    counts: dict[str, int] = {"small": 0, "large": 0}

    async def _count_for(n_extra_churches: int, key: str) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            local_world = await _seed_world(db, n_churches_outside_region=n_extra_churches)
            local_roles = await ensure_acl_roles(db)
            db.add(
                UserRoleAssignmentDB(
                    id=generate_id(),
                    user_id=bishop.id,
                    role_id=local_roles["regional_bishop"].id,
                    scope_type="region",
                    scope_id=local_world["region_id"],
                )
            )
            await db.commit()

            def _on_execute(*_args: object, **_kwargs: object) -> None:
                counts[key] += 1

            event.listen(engine.sync_engine, "before_cursor_execute", _on_execute)
            service = PermissionService(db, PermissionCache(None))
            await service.permissions_for_user(bishop)
            event.remove(engine.sync_engine, "before_cursor_execute", _on_execute)
        await engine.dispose()

    await _count_for(1, "small")
    await _count_for(50, "large")

    assert counts["small"] == counts["large"]
