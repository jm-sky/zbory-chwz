"""G12 — extends the §11 permission matrix (test_permission_matrix.py) with the
governance-module actions it didn't cover: role grant, role revoke, and permission
allow/deny exceptions, for every actor type. Invite/invite-acceptance already have a
dedicated, more thorough test file (test_invite_flow.py) — not duplicated here."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

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
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app

ActorKey = Literal[
    "logged_in",
    "diacon_own",
    "pastor_own",
    "pastor_other",
    "regional_bishop_in",
    "chief_bishop",
    "admin",
]


@dataclass(frozen=True)
class World:
    community_id: str
    region_central_id: str
    church_wawa_id: str
    church_zabrze_id: str
    actor_ids: dict[ActorKey, str]
    target_user_id: str


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> World:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_central_id = generate_id()
    church_wawa_id = generate_id()
    church_zabrze_id = generate_id()

    actor_ids: dict[ActorKey, str] = {
        "logged_in": "user-logged-in",
        "diacon_own": "user-diacon",
        "pastor_own": "user-pastor-wawa",
        "pastor_other": "user-pastor-zabrze",
        "regional_bishop_in": "user-rb-central",
        "chief_bishop": "user-chief",
        "admin": "user-admin",
    }
    target_user_id = "user-grant-target"

    session.add_all(
        [
            *(UserDB(id=uid, email=f"{uid}@example.com", name=uid) for uid in actor_ids.values()),
            UserDB(id=target_user_id, email=f"{target_user_id}@example.com", name="Grant Target"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(id=region_central_id, community_id=community_id, name="Centralny", slug="centralny", created_at=now),
            ChurchDB(
                id=church_wawa_id,
                community_id=community_id,
                region_id=region_central_id,
                tenant_id=church_wawa_id,
                name="Warszawa",
                visibility="public",
                created_at=now,
            ),
            ChurchDB(
                id=church_zabrze_id,
                community_id=community_id,
                region_id=None,
                tenant_id=church_zabrze_id,
                name="Zabrze",
                visibility="public",
                created_at=now,
            ),
        ]
    )
    await session.flush()

    roles = await ensure_acl_roles(session)
    grants = [
        (actor_ids["diacon_own"], "diacon", "church", church_wawa_id),
        (actor_ids["pastor_own"], "pastor", "church", church_wawa_id),
        (actor_ids["pastor_other"], "pastor", "church", church_zabrze_id),
        (actor_ids["regional_bishop_in"], "regional_bishop", "region", region_central_id),
        (actor_ids["chief_bishop"], "bishop", "community", community_id),
    ]
    for user_id, role_name, scope_type, scope_id in grants:
        session.add(
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=user_id,
                role_id=roles[role_name].id,
                scope_type=scope_type,
                scope_id=scope_id,
            )
        )
    await session.commit()

    return World(
        community_id=community_id,
        region_central_id=region_central_id,
        church_wawa_id=church_wawa_id,
        church_zabrze_id=church_zabrze_id,
        actor_ids=actor_ids,
        target_user_id=target_user_id,
    )


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

        async def login(actor: ActorKey | Literal["admin_login"], world: World) -> None:
            if actor == "admin":
                app.dependency_overrides[get_current_user] = lambda: _api_user(world.actor_ids["admin"], is_admin=True)
            else:
                app.dependency_overrides[get_current_user] = lambda: _api_user(world.actor_ids[actor])
            await client.get("/api/auth/csrf-token")

        yield client, login, world

    app.dependency_overrides.clear()
    await engine.dispose()


# Whether each actor can grant/revoke "pastor" at church_wawa_id (church scope).
GRANT_PASTOR_AT_WAWA: dict[ActorKey, bool] = {
    "logged_in": False,
    "diacon_own": False,
    "pastor_own": False,
    "pastor_other": False,
    "regional_bishop_in": True,
    "chief_bishop": True,
    "admin": True,
}

# Whether each actor can set a "church.publish" exception (allow or deny) for the target
# user at church_wawa_id — requires services.manage in scope AND holding church.publish.
SET_EXCEPTION_AT_WAWA: dict[ActorKey, bool] = {
    "logged_in": False,
    "diacon_own": False,
    "pastor_own": False,
    "pastor_other": False,
    "regional_bishop_in": True,
    "chief_bishop": True,
    "admin": True,
}


@pytest.mark.parametrize("actor", list(GRANT_PASTOR_AT_WAWA.keys()))
@pytest.mark.asyncio
async def test_grant_and_revoke_pastor_role_matrix(ctx, actor: ActorKey) -> None:
    client, login, world = ctx
    expected = GRANT_PASTOR_AT_WAWA[actor]

    await login(actor, world)
    grant_response = await client.post(
        "/api/governance/role-assignments",
        json={
            "userId": world.target_user_id,
            "roleName": "pastor",
            "scopeType": "church",
            "scopeId": world.church_wawa_id,
        },
    )

    if expected:
        assert grant_response.status_code == 201, grant_response.text
        assignment_id = grant_response.json()["id"]

        await login(actor, world)
        revoke_response = await client.delete(f"/api/governance/role-assignments/{assignment_id}")
        assert revoke_response.status_code == 204
    else:
        assert grant_response.status_code == 403, grant_response.text


@pytest.mark.parametrize("actor", list(SET_EXCEPTION_AT_WAWA.keys()))
@pytest.mark.parametrize("effect", ["allow", "deny"])
@pytest.mark.asyncio
async def test_permission_exception_matrix(ctx, actor: ActorKey, effect: str) -> None:
    client, login, world = ctx
    expected = SET_EXCEPTION_AT_WAWA[actor]

    await login(actor, world)
    response = await client.put(
        "/api/governance/user-permissions",
        json={
            "userId": world.target_user_id,
            "scopeType": "church",
            "scopeId": world.church_wawa_id,
            "permission": "church.publish",
            "effect": effect,
        },
    )

    if expected:
        assert response.status_code == 200, response.text
        assert response.json()["effect"] == effect

        await login(actor, world)
        clear_response = await client.delete(f"/api/governance/user-permissions/{response.json()['id']}")
        assert clear_response.status_code == 204
    else:
        assert response.status_code == 403, response.text
