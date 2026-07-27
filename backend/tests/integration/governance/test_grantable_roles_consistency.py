"""G12 — for every actor and every scope, the set of roles returned by
GET /churches/grantable-roles must equal exactly the set of roles for which
POST /governance/role-assignments actually succeeds. The two endpoints share one source
of truth (acl_grant_rules._grant_role_denial_reason / can_grant_role), but G0.4's own
tests only exercise the read side — this drives the write side too, for every actor,
to catch any future divergence between "what the UI shows as grantable" and "what the
API will actually let you grant"."""

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
from app.modules.churches.acl_seed import ROLE_SEED, ensure_acl_roles
from app.modules.churches.db_models import ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from main import app


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_id = generate_id()
    church_id = generate_id()

    session.add_all(
        [
            UserDB(id="pastor", email="pastor@example.com", name="Pastor"),
            UserDB(id="diacon", email="diacon@example.com", name="Diacon"),
            UserDB(id="rb", email="rb@example.com", name="RB"),
            UserDB(id="chief", email="chief@example.com", name="Chief"),
            UserDB(id="target", email="target@example.com", name="Target"),
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
    session.add_all(
        [
            UserRoleAssignmentDB(id=generate_id(), user_id="pastor", role_id=roles["pastor"].id, scope_type="church", scope_id=church_id),
            UserRoleAssignmentDB(id=generate_id(), user_id="diacon", role_id=roles["diacon"].id, scope_type="church", scope_id=church_id),
            UserRoleAssignmentDB(id=generate_id(), user_id="rb", role_id=roles["regional_bishop"].id, scope_type="region", scope_id=region_id),
            UserRoleAssignmentDB(id=generate_id(), user_id="chief", role_id=roles["bishop"].id, scope_type="community", scope_id=community_id),
        ]
    )
    await session.commit()
    return {"community_id": community_id, "region_id": region_id, "church_id": church_id}


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

        async def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user
            await client.get("/api/auth/csrf-token")

        yield client, login, world

    app.dependency_overrides.clear()
    await engine.dispose()


ALL_SCOPES = [
    ("community", "community_id"),
    ("region", "region_id"),
    ("church", "church_id"),
]


@pytest.mark.parametrize(
    "actor_login",
    [
        _api_user("pastor"),
        _api_user("diacon"),
        _api_user("rb"),
        _api_user("chief"),
        _api_user("admin", is_admin=True),
    ],
    ids=["pastor", "diacon", "rb", "chief", "admin"],
)
@pytest.mark.asyncio
async def test_grantable_roles_matches_what_post_actually_allows(ctx, actor_login: User) -> None:
    client, login, world = ctx

    for scope_type, world_key in ALL_SCOPES:
        scope_id = world[world_key]
        candidate_roles = [name for name, role_scope_type, _ in ROLE_SEED if role_scope_type == scope_type]

        await login(actor_login)
        grantable_response = await client.get(
            "/api/churches/grantable-roles",
            params={"scopeType": scope_type, "scopeId": scope_id},
        )
        assert grantable_response.status_code == 200, grantable_response.text
        grantable_names = {r["name"] for r in grantable_response.json()}
        assert grantable_names.issubset(set(candidate_roles))

        for role_name in candidate_roles:
            await login(actor_login)
            post_response = await client.post(
                "/api/governance/role-assignments",
                json={"userId": "target", "roleName": role_name, "scopeType": scope_type, "scopeId": scope_id},
            )
            if role_name in grantable_names:
                assert post_response.status_code == 201, f"{actor_login.id} expected to grant {role_name}@{scope_type}:{scope_id} " f"(listed in grantable-roles) but got {post_response.status_code}: {post_response.text}"
                # Clean up so later scope/role combinations aren't blocked by the
                # "already granted" 409 (unrelated to this test's assertion).
                await login(actor_login)
                await client.delete(f"/api/governance/role-assignments/{post_response.json()['id']}")
            else:
                assert post_response.status_code == 403, f"{actor_login.id} was NOT expected to grant {role_name}@{scope_type}:{scope_id} " f"(absent from grantable-roles) but got {post_response.status_code}: {post_response.text}"
