"""Integration tests for creating, listing, and revoking congregation share links."""

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
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

TENANT_ID = "church-shared"
MEMBER_ID = "user-member"
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
    session.add_all(
        [
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
            TenantDB(id=TENANT_ID, name="Zbor Testowy", status="published", owner_id=MEMBER_ID, created_at=now),
        ]
    )
    session.add(TenantMembershipDB(tenant_id=TENANT_ID, user_id=MEMBER_ID, role="member"))
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
async def test_member_can_create_share_link(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/share-links",
        json={"visibility_level": "public", "expires_in_days": 7, "label": "For a friend"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["visibility_level"] == "public"
    assert data["label"] == "For a friend"
    assert len(data["token"]) >= 32
    assert data["revoked_at"] is None


@pytest.mark.asyncio
async def test_outsider_cannot_create_share_link(ctx) -> None:
    client, login = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/share-links",
        json={"visibility_level": "public", "expires_in_days": 7, "label": None},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pastors_visibility_level_is_rejected(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/share-links",
        json={"visibility_level": "pastors", "expires_in_days": 7, "label": None},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_expiry_preset_is_rejected(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/congregations/{TENANT_ID}/share-links",
        json={"visibility_level": "public", "expires_in_days": 90, "label": None},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_shows_only_active_links(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    create_response = await client.post(
        f"/api/congregations/{TENANT_ID}/share-links",
        json={"visibility_level": "authenticated", "expires_in_days": 3, "label": None},
    )
    link_id = create_response.json()["id"]

    list_response = await client.get(f"/api/congregations/{TENANT_ID}/share-links")
    assert list_response.status_code == 200
    assert [link["id"] for link in list_response.json()["links"]] == [link_id]

    revoke_response = await client.delete(f"/api/congregations/{TENANT_ID}/share-links/{link_id}")
    assert revoke_response.status_code == 204

    list_after_revoke = await client.get(f"/api/congregations/{TENANT_ID}/share-links")
    assert list_after_revoke.json()["links"] == []


@pytest.mark.asyncio
async def test_revoking_unknown_link_returns_404(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.delete(f"/api/congregations/{TENANT_ID}/share-links/{generate_id()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_create_global_share_link(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID, is_admin=True))

    response = await client.post(
        "/api/share-links",
        json={"visibility_level": "public", "expires_in_days": 7, "label": "All congregations"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["visibility_level"] == "public"
    assert data["label"] == "All congregations"


@pytest.mark.asyncio
async def test_non_admin_cannot_create_global_share_link(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        "/api/share-links",
        json={"visibility_level": "public", "expires_in_days": 7, "label": None},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_global_share_links_list_and_revoke_are_scoped_to_creator(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID, is_admin=True))

    create_response = await client.post(
        "/api/share-links",
        json={"visibility_level": "authenticated", "expires_in_days": 3, "label": None},
    )
    link_id = create_response.json()["id"]

    list_response = await client.get("/api/share-links")
    assert list_response.status_code == 200
    assert [link["id"] for link in list_response.json()["links"]] == [link_id]

    login(_api_user(OUTSIDER_ID, is_admin=True))
    other_admin_list = await client.get("/api/share-links")
    assert other_admin_list.json()["links"] == []

    revoke_response = await client.delete(f"/api/share-links/{link_id}")
    assert revoke_response.status_code == 404

    login(_api_user(MEMBER_ID, is_admin=True))
    revoke_response = await client.delete(f"/api/share-links/{link_id}")
    assert revoke_response.status_code == 204

    list_after_revoke = await client.get("/api/share-links")
    assert list_after_revoke.json()["links"] == []
