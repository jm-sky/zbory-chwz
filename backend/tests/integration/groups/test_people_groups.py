"""Integration tests for the people groups module.

Covers the decisions from docs/plans/2026-07-09--people-groups.md:
- visibility is configurable per group (public/authenticated/private)
- membership is ACL-neutral (no permission side effects)
- owner/admin create groups and can designate a steward who manages
  that group's members without needing full admin rights
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

from app.core.database import Base, get_db
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from main import app

ADMIN_ID = "user-admin"
STEWARD_ID = "user-steward"
MEMBER_ID = "user-member"
OUTSIDER_ID = "user-outsider"


def _api_user(user_id: str, *, is_admin: bool = False, is_owner: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        isOwner=is_owner,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> None:
    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin", is_admin=True),
            UserDB(id=STEWARD_ID, email="steward@example.com", name="Steward"),
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
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
async def test_outsider_cannot_create_group(ctx) -> None:
    client, login = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.post("/api/people-groups", json={"name": "Prezydium Rady Naczelnej"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_creates_group_with_steward(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/people-groups",
        json={
            "name": "Grupa Ewangelizacji",
            "visibility": "authenticated",
            "stewardUserId": STEWARD_ID,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "grupa-ewangelizacji"
    assert body["stewardUserId"] == STEWARD_ID
    assert body["memberCount"] == 0


@pytest.mark.asyncio
async def test_private_group_hidden_from_outsider_but_visible_to_steward(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    created = await client.post(
        "/api/people-groups",
        json={
            "name": "Prezydium Rady Naczelnej",
            "visibility": "private",
            "stewardUserId": STEWARD_ID,
        },
    )
    group_id = created.json()["id"]

    login(_api_user(OUTSIDER_ID))
    hidden = await client.get(f"/api/people-groups/{group_id}")
    assert hidden.status_code == 403

    listing = await client.get("/api/people-groups")
    assert listing.status_code == 200
    assert all(g["id"] != group_id for g in listing.json())

    login(_api_user(STEWARD_ID))
    visible = await client.get(f"/api/people-groups/{group_id}")
    assert visible.status_code == 200


@pytest.mark.asyncio
async def test_steward_can_manage_members_but_not_group_metadata(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    created = await client.post(
        "/api/people-groups",
        json={"name": "Sluzba Wiezienna", "stewardUserId": STEWARD_ID},
    )
    group_id = created.json()["id"]

    login(_api_user(STEWARD_ID))

    # Steward manages membership.
    added = await client.post(
        f"/api/people-groups/{group_id}/memberships",
        json={
            "firstName": "Jan",
            "lastName": "Kowalski",
            "roleLabel": "Koordynator",
        },
    )
    assert added.status_code == 201
    membership_id = added.json()["id"]
    assert added.json()["roleLabel"] == "Koordynator"

    detail = await client.get(f"/api/people-groups/{group_id}")
    assert detail.json()["memberCount"] == 1

    # But cannot edit group metadata — that stays admin/owner only.
    forbidden = await client.patch(f"/api/people-groups/{group_id}", json={"name": "Renamed"})
    assert forbidden.status_code == 403

    removed = await client.delete(f"/api/people-groups/{group_id}/memberships/{membership_id}")
    assert removed.status_code == 204

    detail_after = await client.get(f"/api/people-groups/{group_id}")
    assert detail_after.json()["memberCount"] == 0


@pytest.mark.asyncio
async def test_regular_member_cannot_manage_group_members(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    created = await client.post("/api/people-groups", json={"name": "Grupa Modlitwy"})
    group_id = created.json()["id"]

    login(_api_user(MEMBER_ID))
    response = await client.post(
        f"/api/people-groups/{group_id}/memberships",
        json={"firstName": "Anna", "lastName": "Nowak"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_active_membership_rejected(ctx) -> None:
    client, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    created = await client.post("/api/people-groups", json={"name": "Chor"})
    group_id = created.json()["id"]

    first = await client.post(
        f"/api/people-groups/{group_id}/memberships",
        json={"firstName": "Ewa", "lastName": "Zielinska"},
    )
    person_id = first.json()["personId"]

    duplicate = await client.post(
        f"/api/people-groups/{group_id}/memberships",
        json={"personId": person_id},
    )

    assert duplicate.status_code == 409
