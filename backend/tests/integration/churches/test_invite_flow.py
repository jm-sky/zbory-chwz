"""G2 — invite endpoint + accept-invite flow: invite -> accept -> login works; re-invite
invalidates the previous token; expired token rejected; missing permission -> 403;
assignment from another church -> 404; response never contains the token; acceptance
touches no ACL row."""

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_POOL_SIZE", "1")
os.environ.setdefault("DATABASE_MAX_OVERFLOW", "0")

from app.common.id_utils import generate_id
from app.core.auth.dependencies import get_token_blacklist_service
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.modules.auth.auth_utils import get_password_hash, verify_password
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, ServiceAssignmentDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app


class FakeAsyncRedis:
    """Avoids the real-Redis event-loop flake seen elsewhere in this suite
    (permission cache depends on get_redis)."""

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
    other_church_id = generate_id()
    invitee_user_id = generate_id()
    assignment_id = generate_id()
    no_account_assignment_id = generate_id()

    session.add_all(
        [
            UserDB(id="pastor", email="pastor@example.com", name="Pastor", is_active=True),
            UserDB(
                id=invitee_user_id,
                email="invitee@example.com",
                name="Invitee",
                is_active=False,
                hashed_password=get_password_hash("random-unknown-password-1!"),
            ),
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
            ChurchDB(
                id=other_church_id,
                community_id=community_id,
                region_id=None,
                tenant_id=other_church_id,
                name="Zabrze",
                visibility="public",
                created_at=now,
            ),
        ]
    )
    await session.flush()

    person = PersonDB(id=generate_id(), first_name="Jan", last_name="Kowalski", email="invitee@example.com", user_id=invitee_user_id)
    person_no_account = PersonDB(id=generate_id(), first_name="Adam", last_name="Nowak", email="noaccount@example.com")
    session.add_all([person, person_no_account])
    await session.flush()

    session.add_all(
        [
            ServiceAssignmentDB(
                id=assignment_id,
                person_id=person.id,
                custom_service_name="Custom Role",
                scope_type="church",
                scope_id=church_id,
            ),
            ServiceAssignmentDB(
                id=no_account_assignment_id,
                person_id=person_no_account.id,
                custom_service_name="No Account Role",
                scope_type="church",
                scope_id=church_id,
            ),
        ]
    )

    roles = await ensure_acl_roles(session)
    session.add(UserRoleAssignmentDB(id=generate_id(), user_id="pastor", role_id=roles["pastor"].id, scope_type="church", scope_id=church_id))
    await session.commit()

    return {
        "church_id": church_id,
        "other_church_id": other_church_id,
        "assignment_id": assignment_id,
        "no_account_assignment_id": no_account_assignment_id,
        "invitee_user_id": invitee_user_id,
        "invitee_email": "invitee@example.com",
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

    fake_redis = FakeAsyncRedis()

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_token_blacklist_service] = lambda: AsyncMock(blacklist_all_user_tokens=AsyncMock(return_value=0))

    def override_permission_service(db: AsyncSession = Depends(get_db)) -> PermissionService:
        return PermissionService(db, PermissionCache(None))

    app.dependency_overrides[get_permission_service] = override_permission_service

    async with session_factory() as session:
        world = await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, login, world, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_invite_response_never_contains_token(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    response = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"invitedAt", "invitationExpiresAt"}
    assert "token" not in str(body)


@pytest.mark.asyncio
async def test_missing_permission_is_403(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("nobody"))

    response = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_assignment_from_other_church_is_404(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    response = await client.post(f"/api/churches/{world['other_church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_account_is_409(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    response = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['no_account_assignment_id']}/invite")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invite_then_accept_then_login_works(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    invite_response = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert invite_response.status_code == 200

    async with session_factory() as session:
        user_db = (await session.execute(select(UserDB).where(UserDB.id == world["invitee_user_id"]))).scalar_one()
        assert user_db.is_active is False
        token = user_db.invite_token
        assert token

    accept_response = await client.post("/api/auth/accept-invite", json={"token": token, "password": "NewStrongPass1!"})
    assert accept_response.status_code == 200

    async with session_factory() as session:
        user_db = (await session.execute(select(UserDB).where(UserDB.id == world["invitee_user_id"]))).scalar_one()
        assert user_db.is_active is True
        assert user_db.is_email_verified is True
        assert user_db.invite_token is None
        assert user_db.token_version == 1
        assert verify_password("NewStrongPass1!", user_db.hashed_password)

        role_count = (await session.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.user_id == world["invitee_user_id"]))).scalars().all()
        perm_count = (await session.execute(select(UserPermissionDB).where(UserPermissionDB.user_id == world["invitee_user_id"]))).scalars().all()
        assert role_count == []
        assert perm_count == []


@pytest.mark.asyncio
async def test_reinvite_invalidates_previous_token(ctx) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    first = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert first.status_code == 200
    async with session_factory() as session:
        first_token = (await session.execute(select(UserDB).where(UserDB.id == world["invitee_user_id"]))).scalar_one().invite_token

    # JWT `iat`/`exp` have 1-second resolution — without this, a same-second re-invite
    # would mint a byte-identical token and this test couldn't tell "invalidated" from
    # "coincidentally equal".
    await asyncio.sleep(1.1)

    second = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert second.status_code == 200
    async with session_factory() as session:
        second_token = (await session.execute(select(UserDB).where(UserDB.id == world["invitee_user_id"]))).scalar_one().invite_token

    assert first_token != second_token

    stale_accept = await client.post("/api/auth/accept-invite", json={"token": first_token, "password": "NewStrongPass1!"})
    assert stale_accept.status_code == 400

    fresh_accept = await client.post("/api/auth/accept-invite", json={"token": second_token, "password": "NewStrongPass1!"})
    assert fresh_accept.status_code == 200


@pytest.mark.asyncio
async def test_expired_invite_token_is_rejected(ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    client, login, world, session_factory = ctx
    login(_api_user("pastor"))

    monkeypatch.setattr(settings.security, "invite_token_expires_hours", -1)
    invite_response = await client.post(f"/api/churches/{world['church_id']}/service-assignments/{world['assignment_id']}/invite")
    assert invite_response.status_code == 200

    async with session_factory() as session:
        token = (await session.execute(select(UserDB).where(UserDB.id == world["invitee_user_id"]))).scalar_one().invite_token

    accept_response = await client.post("/api/auth/accept-invite", json={"token": token, "password": "NewStrongPass1!"})
    assert accept_response.status_code == 400
