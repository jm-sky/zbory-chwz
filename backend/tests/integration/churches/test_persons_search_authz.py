"""Authorization tests for GET /churches/persons/search.

Regression cover for SEC-4 (docs/issues/2026-07-10--017): the endpoint used
to be reachable by any logged-in account with any ACL role, turning it into
a scraper for the whole persons directory. It must now also require the
`services.manage` permission (admin/owner always pass).
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
from app.modules.churches.db_models import (
    ChurchDB,
    CommunityDB,
    PersonDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from main import app

ADMIN_ID = "user-admin"
BISHOP_ID = "user-bishop"
PASTOR_ID = "user-pastor"
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
    church_id = generate_id()
    pastor_type_id = generate_id()

    person = PersonDB(id=generate_id(), first_name="Jan", last_name="Kowalski", email="jan@example.com")

    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin"),
            UserDB(id=BISHOP_ID, email="bishop@example.com", name="Bishop"),
            UserDB(id=PASTOR_ID, email="pastor@example.com", name="Pastor"),
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                tenant_id=church_id,
                name="Zbor",
                visibility="public",
                created_at=now,
            ),
            ServiceTypeDB(
                id=pastor_type_id,
                slug="pastor",
                name="Pastor",
                scope_type="church",
                sort_order=1,
            ),
            person,
        ]
    )
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=person.id,
            service_type_id=pastor_type_id,
            scope_type="church",
            scope_id=church_id,
            profile_visibility="public",
            phone_visibility="public",
            email_visibility="hidden",
            created_at=now,
        )
    )

    roles = await ensure_acl_roles(session)
    session.add_all(
        [
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=BISHOP_ID,
                role_id=roles["bishop"].id,
                scope_type="community",
                scope_id=community_id,
                created_at=now,
            ),
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=PASTOR_ID,
                role_id=roles["pastor"].id,
                scope_type="church",
                scope_id=church_id,
                created_at=now,
            ),
        ]
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
async def test_outsider_without_acl_is_denied(ctx) -> None:
    client, login = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.get("/api/churches/persons/search", params={"q": "Jan"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pastor_without_services_manage_is_denied(ctx) -> None:
    """A plain pastoral ACL role isn't enough — `services.manage` is required."""
    client, login = ctx
    login(_api_user(PASTOR_ID))

    response = await client.get("/api/churches/persons/search", params={"q": "Jan"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bishop_with_services_manage_is_allowed(ctx) -> None:
    client, login = ctx
    login(_api_user(BISHOP_ID))

    response = await client.get("/api/churches/persons/search", params={"q": "Jan"})

    assert response.status_code == 200
    names = [p["firstName"] for p in response.json()["persons"]]
    assert "Jan" in names


@pytest.mark.asyncio
async def test_admin_is_always_allowed(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get("/api/churches/persons/search", params={"q": "Jan"})

    assert response.status_code == 200
