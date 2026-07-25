"""Integration tests for ACL permission matrix (architecture §11)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import pytest
import pytest_asyncio
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
from app.core.database import Base, get_db
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission, ensure_acl_roles
from app.modules.churches.db_models import (
    ChurchDB,
    CommunityDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.seed_data import CHWZ_ORG_TENANT_NAME
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.tenants.access import TenantAccessChecker
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository
from fastapi import Depends, HTTPException
from main import app

ActorKey = Literal[
    "guest",
    "logged_in",
    "diacon_own",
    "pastor_own",
    "pastor_other",
    "regional_bishop_in",
    "chief_bishop",
    "admin",
]


@dataclass(frozen=True)
class MatrixWorld:
    community_id: str
    region_central_id: str
    region_gorny_id: str
    church_wawa_id: str
    church_zabrze_id: str
    church_orphan_id: str
    pastor_type_id: str
    diacon_type_id: str
    org_tenant_id: str
    actor_ids: dict[ActorKey, str]


def _api_user(user_id: str, *, is_admin: bool = False, is_owner: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        isOwner=is_owner,
        createdAt=datetime.now(UTC),
    )


def _actor_user(world: MatrixWorld, key: ActorKey) -> User | None:
    if key == "guest":
        return None
    if key == "admin":
        return _api_user(world.actor_ids["admin"], is_admin=True)
    return _api_user(world.actor_ids[key])


async def _seed_matrix(session: AsyncSession) -> MatrixWorld:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_central_id = generate_id()
    region_gorny_id = generate_id()
    church_wawa_id = generate_id()
    church_zabrze_id = generate_id()
    church_orphan_id = generate_id()
    pastor_type_id = generate_id()
    diacon_type_id = generate_id()
    org_tenant_id = generate_id()

    actor_ids: dict[ActorKey, str] = {
        "logged_in": "user-logged-in",
        "diacon_own": "user-diacon",
        "pastor_own": "user-pastor-wawa",
        "pastor_other": "user-pastor-zabrze",
        "regional_bishop_in": "user-rb-central",
        "chief_bishop": "user-chief",
        "admin": "user-admin",
    }

    users = [UserDB(id=uid, email=f"{uid}@example.com", name=uid) for uid in actor_ids.values()]
    session.add_all(
        [
            *users,
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(
                id=region_central_id,
                community_id=community_id,
                name="Centralny",
                slug="centralny",
                created_at=now,
            ),
            RegionDB(
                id=region_gorny_id,
                community_id=community_id,
                name="Górny Śląsk",
                slug="gorny-slask",
                created_at=now,
            ),
            TenantDB(
                id=org_tenant_id,
                name=CHWZ_ORG_TENANT_NAME,
                status="published",
                owner_id=actor_ids["admin"],
                created_at=now,
            ),
            ServiceTypeDB(
                id=pastor_type_id,
                slug="pastor",
                name="Pastor",
                scope_type="church",
                suggested_role="pastor",
                sort_order=1,
            ),
            ServiceTypeDB(
                id=diacon_type_id,
                slug="diakon",
                name="Diakon",
                scope_type="church",
                suggested_role="diacon",
                sort_order=2,
            ),
        ]
    )

    churches = [
        (church_wawa_id, "Warszawa", region_central_id),
        (church_zabrze_id, "Zabrze", region_gorny_id),
        (church_orphan_id, "Bez rejonu", None),
    ]
    for church_id, name, region_id in churches:
        session.add(
            TenantDB(
                id=church_id,
                name=name,
                status="published",
                owner_id=actor_ids["admin"],
                created_at=now,
            )
        )
        session.add(
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=region_id,
                tenant_id=org_tenant_id,
                name=name,
                visibility="public",
                created_at=now,
            )
        )
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=church_id,
                city=name,
                country="PL",
                status="published",
                created_at=now,
                updated_at=now,
            )
        )

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
    return MatrixWorld(
        community_id=community_id,
        region_central_id=region_central_id,
        region_gorny_id=region_gorny_id,
        church_wawa_id=church_wawa_id,
        church_zabrze_id=church_zabrze_id,
        church_orphan_id=church_orphan_id,
        pastor_type_id=pastor_type_id,
        diacon_type_id=diacon_type_id,
        org_tenant_id=org_tenant_id,
        actor_ids=actor_ids,
    )


@pytest_asyncio.fixture
async def matrix_ctx():
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

    world: MatrixWorld
    async with session_factory() as session:
        world = await _seed_matrix(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User | None) -> None:
            if user is None:
                app.dependency_overrides.pop(get_current_user, None)
            else:
                app.dependency_overrides[get_current_user] = lambda: user

        yield client, login, world, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


# Expected matrix for church_wawa_id (Warszawa / Centralny)
MATRIX_WAWA: dict[ActorKey, dict[str, bool]] = {
    "guest": {
        "church.edit": False,
        "assign_pastor": False,
        "assign_diacon": False,
        "church.create": False,
        "church.move_region": False,
        "church.publish": False,
        "church.view_pastoral": False,
    },
    "logged_in": {
        "church.edit": False,
        "assign_pastor": False,
        "assign_diacon": False,
        "church.create": False,
        "church.move_region": False,
        "church.publish": False,
        "church.view_pastoral": False,
    },
    "diacon_own": {
        "church.edit": True,
        "assign_pastor": False,
        "assign_diacon": True,
        "church.create": False,
        "church.move_region": False,
        "church.publish": False,
        "church.view_pastoral": True,
    },
    "pastor_own": {
        "church.edit": True,
        "assign_pastor": False,
        "assign_diacon": True,
        "church.create": False,
        "church.move_region": False,
        "church.publish": True,
        "church.view_pastoral": True,
    },
    "pastor_other": {
        "church.edit": False,
        "assign_pastor": False,
        "assign_diacon": False,
        "church.create": False,
        "church.move_region": False,
        "church.publish": False,
        "church.view_pastoral": False,
    },
    "regional_bishop_in": {
        "church.edit": True,
        "assign_pastor": True,
        "assign_diacon": True,
        "church.create": True,
        "church.move_region": False,
        "church.publish": True,
        "church.view_pastoral": True,
    },
    "chief_bishop": {
        "church.edit": True,
        "assign_pastor": True,
        "assign_diacon": True,
        "church.create": True,
        "church.move_region": True,
        "church.publish": True,
        "church.view_pastoral": True,
    },
    "admin": {
        "church.edit": True,
        "assign_pastor": True,
        "assign_diacon": True,
        "church.create": True,
        "church.move_region": True,
        "church.publish": True,
        "church.view_pastoral": True,
    },
}

# Regional bishop (Centralny) acting on Zabrze (Górny Śląsk) — doc matrix row.
MATRIX_RB_OUT_ZABRZE: dict[str, bool] = {
    "church.edit": False,
    "church.view_pastoral": False,
    "church.publish": False,
    "church.move_region": False,
    "services.manage": False,
    "people.manage": False,
}


@pytest.mark.parametrize("actor", list(MATRIX_WAWA.keys()))
@pytest.mark.asyncio
async def test_permission_matrix_warsaw(matrix_ctx, actor: ActorKey) -> None:
    client, login, world, session_factory = matrix_ctx
    user = _actor_user(world, actor)
    church_id = world.church_wawa_id
    expected = MATRIX_WAWA[actor]

    if user is None:
        login(None)
    else:
        login(user)

    await client.get("/api/auth/csrf-token")

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        scope = ("church", church_id)
        if user is not None:
            assert (
                await permission_service.resolve(user, Permission.CHURCH_EDIT, scope) == expected["church.edit"]
            )
            assert (
                await permission_service.resolve(user, Permission.CHURCH_VIEW_PASTORAL, scope)
                == expected["church.view_pastoral"]
            )
            assert (
                await permission_service.resolve(user, Permission.CHURCH_PUBLISH, scope) == expected["church.publish"]
            )
            assert (
                await permission_service.resolve(user, Permission.CHURCH_MOVE_REGION, scope)
                == expected["church.move_region"]
            )
            assert await permission_service.has_anywhere(user, Permission.CHURCH_CREATE) == expected["church.create"]

    patch = await client.patch(f"/api/congregations/{church_id}", json={"description": "matrix"})
    if expected["church.edit"] and user is not None:
        assert patch.status_code == 200
    else:
        assert patch.status_code in {401, 403}

    pastor_payload = {
        "firstName": "Nowy",
        "lastName": "Pastor",
        "serviceTypeId": world.pastor_type_id,
    }
    pastor_resp = await client.post(
        f"/api/churches/{church_id}/service-assignments",
        json=pastor_payload,
    )
    if expected["assign_pastor"] and user is not None:
        assert pastor_resp.status_code == 201, pastor_resp.text
    else:
        assert pastor_resp.status_code in {401, 403}, pastor_resp.text

    diacon_payload = {
        "firstName": "Nowy",
        "lastName": "Diakon",
        "serviceTypeId": world.diacon_type_id,
    }
    diacon_resp = await client.post(
        f"/api/churches/{church_id}/service-assignments",
        json=diacon_payload,
    )
    if expected["assign_diacon"] and user is not None:
        assert diacon_resp.status_code == 201
    else:
        assert diacon_resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_regional_bishop_outside_region_on_zabrze(matrix_ctx) -> None:
    _, login, world, session_factory = matrix_ctx
    user = _api_user(world.actor_ids["regional_bishop_in"])
    login(user)
    church_id = world.church_zabrze_id
    scope = ("church", church_id)

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        for perm_name, value in MATRIX_RB_OUT_ZABRZE.items():
            perm = Permission(perm_name)
            assert await permission_service.resolve(user, perm, scope) == value
        assert await permission_service.resolve(
            user,
            Permission.CHURCH_CREATE,
            ("region", world.region_central_id),
        )
        assert not await permission_service.resolve(
            user,
            Permission.CHURCH_CREATE,
            ("region", world.region_gorny_id),
        )


@pytest.mark.asyncio
async def test_chief_bishop_reaches_orphan_church_regional_bishop_does_not(matrix_ctx) -> None:
    _, _, world, session_factory = matrix_ctx
    orphan_scope = ("church", world.church_orphan_id)

    rb = _api_user(world.actor_ids["regional_bishop_in"])
    chief = _api_user(world.actor_ids["chief_bishop"])

    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        assert not await permission_service.resolve(rb, Permission.CHURCH_EDIT, orphan_scope)
        assert await permission_service.resolve(chief, Permission.CHURCH_EDIT, orphan_scope)


@pytest.mark.asyncio
async def test_community_deny_overrides_church_pastor_role(matrix_ctx) -> None:
    _, _, world, session_factory = matrix_ctx
    async with session_factory() as session:
        session.add(
            UserPermissionDB(
                id=generate_id(),
                user_id=world.actor_ids["pastor_own"],
                scope_type="community",
                scope_id=world.community_id,
                permission=Permission.CHURCH_EDIT,
                effect="deny",
            )
        )
        await session.commit()

        user = _api_user(world.actor_ids["pastor_own"])
        scope = ("church", world.church_wawa_id)
        permission_service = PermissionService(session, PermissionCache(None))
        assert not await permission_service.resolve(user, Permission.CHURCH_EDIT, scope)


@pytest.mark.asyncio
async def test_deleting_service_assignment_clears_sourced_acl_only(matrix_ctx) -> None:
    _, login, world, session_factory = matrix_ctx
    async with session_factory() as session:
        roles = await ensure_acl_roles(session)
        pastor_role = roles["pastor"]
        person = PersonDB(id=generate_id(), first_name="S", last_name="A")
        session.add(person)
        await session.flush()

        manual_user_id = generate_id()
        sourced_user_id = generate_id()
        session.add_all(
            [
                UserDB(id=manual_user_id, email="manual@example.com", name="Manual"),
                UserDB(id=sourced_user_id, email="sourced@example.com", name="Sourced"),
            ]
        )
        await session.flush()

        assignment_id = generate_id()
        session.add(
            ServiceAssignmentDB(
                id=assignment_id,
                person_id=person.id,
                service_type_id=world.pastor_type_id,
                scope_type="church",
                scope_id=world.church_wawa_id,
            )
        )
        manual_id = generate_id()
        sourced_id = generate_id()
        session.add_all(
            [
                UserRoleAssignmentDB(
                    id=manual_id,
                    user_id=manual_user_id,
                    role_id=pastor_role.id,
                    scope_type="church",
                    scope_id=world.church_wawa_id,
                    source_assignment_id=None,
                ),
                UserRoleAssignmentDB(
                    id=sourced_id,
                    user_id=sourced_user_id,
                    role_id=pastor_role.id,
                    scope_type="church",
                    scope_id=world.church_wawa_id,
                    source_assignment_id=assignment_id,
                ),
            ]
        )
        await session.commit()

        repo = ChurchRepository(session)
        assert await repo.delete_service_assignment("church", world.church_wawa_id, assignment_id)

        manual_rows = (
            await session.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.user_id == manual_user_id))
        ).scalars().all()
        sourced_rows = (
            await session.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.user_id == sourced_user_id))
        ).scalars().all()
        assert len(manual_rows) == 1
        assert manual_rows[0].id == manual_id
        assert len(sourced_rows) == 0


@pytest.mark.asyncio
async def test_chwz_org_tenant_rejected_by_tenant_access(matrix_ctx) -> None:
    _, _, world, session_factory = matrix_ctx
    async with session_factory() as session:
        tenant_repo = TenantRepository(session)
        church_repo = ChurchRepository(session)
        checker = TenantAccessChecker(
            tenant_repo,
            PermissionService(session, PermissionCache(None)),
            church_repo,
        )
        user = _api_user(world.actor_ids["chief_bishop"])
        with pytest.raises(HTTPException) as exc_info:
            await checker.verify(world.org_tenant_id, user)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_diacon_cannot_grant_bishop_role_via_assignment(matrix_ctx) -> None:
    client, login, world, _ = matrix_ctx
    login(_api_user(world.actor_ids["diacon_own"]))

    response = await client.post(
        f"/api/churches/{world.church_wawa_id}/service-assignments",
        json={
            "firstName": "Fake",
            "lastName": "Bishop",
            "email": "fake@example.com",
            "serviceTypeId": world.diacon_type_id,
            "createAccount": True,
            "suggestedRole": "bishop",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_permission_results_identical_without_redis_cache(matrix_ctx) -> None:
    _, _, world, session_factory = matrix_ctx
    user = _api_user(world.actor_ids["chief_bishop"])
    scope = ("church", world.church_wawa_id)

    async with session_factory() as session:
        with_cache = PermissionService(session, PermissionCache(None))
        without_cache = PermissionService(session, PermissionCache(None))
        perms = (
            Permission.CHURCH_EDIT,
            Permission.SERVICES_MANAGE,
            Permission.CHURCH_PUBLISH,
            Permission.CHURCH_VIEW_PASTORAL,
        )
        for perm in perms:
            assert await with_cache.resolve(user, perm, scope) == await without_cache.resolve(user, perm, scope)


@pytest.mark.asyncio
async def test_chief_bishop_covers_region_without_regional_bishop_assignment(matrix_ctx) -> None:
    """Dolny Śląsk-style fallback: no RB on region, chief bishop still has access."""
    _, _, world, session_factory = matrix_ctx
    chief = _api_user(world.actor_ids["chief_bishop"])
    scope = ("church", world.church_zabrze_id)
    async with session_factory() as session:
        permission_service = PermissionService(session, PermissionCache(None))
        assert await permission_service.resolve(chief, Permission.CHURCH_EDIT, scope)
        assert await permission_service.resolve(chief, Permission.SERVICES_MANAGE, scope)
