"""Authorization tests for POST /tenants (public congregation creation).

Regression cover for SEC-5 (docs/issues/2026-07-10--017): governance reserves
founding a congregation for bishops and global admins/owners, but the public
endpoint used to accept any logged-in account.
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
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import CommunityDB
from main import app

ADMIN_ID = "user-admin"
BISHOP_ID = "user-bishop"
OUTSIDER_ID = "user-outsider"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()

    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin"),
            UserDB(id=BISHOP_ID, email="bishop@example.com", name="Bishop"),
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
        ]
    )
    await session.flush()

    roles = await ensure_acl_roles(session)
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=BISHOP_ID,
            role_id=roles["bishop"].id,
            scope_type="community",
            scope_id=community_id,
            created_at=now,
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
async def test_outsider_cannot_create_tenant(ctx) -> None:
    client, login = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.post("/api/tenants", json={"name": "Nowy Zbor"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bishop_with_church_create_can_create_tenant(ctx) -> None:
    client, login = ctx
    login(_api_user(BISHOP_ID))

    response = await client.post("/api/tenants", json={"name": "Nowy Zbor"})

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_admin_can_create_tenant(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post("/api/tenants", json={"name": "Nowy Zbor"})

    assert response.status_code == 201
