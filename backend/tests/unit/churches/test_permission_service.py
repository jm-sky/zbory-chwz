"""Unit tests for PermissionService scope resolution."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission, ensure_acl_roles
from app.modules.churches.db_models import BranchDB, ChurchDB, CommunityDB, RegionDB
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
    return User(
        id=user_id,
        email="u@example.com",
        name="User",
        isAdmin=False,
        createdAt=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_deny_on_community_blocks_pastor_on_church(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(id=region_id, community_id=community_id, name="Centralny", slug="centralny", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=region_id,
                tenant_id=church_id,
                name="Zbor",
                visibility="hidden",
                created_at=now,
            ),
        ]
    )
    await session.flush()
    roles = await ensure_acl_roles(session)
    user = _user()
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=user.id,
            role_id=roles["pastor"].id,
            scope_type="church",
            scope_id=church_id,
        )
    )
    session.add(
        UserPermissionDB(
            id=generate_id(),
            user_id=user.id,
            scope_type="community",
            scope_id=community_id,
            permission=Permission.CHURCH_EDIT,
            effect="deny",
        )
    )
    await session.commit()

    service = PermissionService(session, PermissionCache(None))
    assert not await service.resolve(user, Permission.CHURCH_EDIT, ("church", church_id))


@pytest.mark.asyncio
async def test_regional_bishop_reaches_church_in_region(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
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
    bishop = _user("rb")
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=bishop.id,
            role_id=roles["regional_bishop"].id,
            scope_type="region",
            scope_id=region_id,
        )
    )
    await session.commit()

    service = PermissionService(session, PermissionCache(None))
    assert await service.resolve(bishop, Permission.CHURCH_EDIT, ("church", church_id))


@pytest.mark.asyncio
async def test_branch_responsible_scoped_to_own_branch(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    church_id = generate_id()
    branch_id = generate_id()
    other_branch_id = generate_id()

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
            BranchDB(id=branch_id, church_id=church_id, name="Placowka", slug="placowka", created_at=now),
            BranchDB(
                id=other_branch_id,
                church_id=church_id,
                name="Inna placowka",
                slug="inna-placowka",
                created_at=now,
            ),
        ]
    )
    await session.flush()
    roles = await ensure_acl_roles(session)
    user = _user("branch-responsible")
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=user.id,
            role_id=roles["branch_responsible"].id,
            scope_type="branch",
            scope_id=branch_id,
        )
    )
    await session.commit()

    service = PermissionService(session, PermissionCache(None))
    assert await service.resolve(user, Permission.BRANCH_MANAGE, ("branch", branch_id))
    assert not await service.resolve(user, Permission.BRANCH_MANAGE, ("branch", other_branch_id))
