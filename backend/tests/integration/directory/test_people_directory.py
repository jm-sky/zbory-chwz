"""Integration tests for the people directory (email export) module.

Covers the 2026-07-11 decisions from docs/plans/2026-07-09--mailing-lists.md:
access is scoped by the existing ACL (user_role_assignments) — pastor/diacon
see only their own church, regional_bishop their region, bishop their
community, admin/owner everything; users with no ACL role are denied.
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
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.groups.db_models import PeopleGroupDB, PeopleGroupMembershipDB
from main import app

ADMIN_ID = "user-admin"
PASTOR_A1_ID = "user-pastor-a1"
BISHOP_NORTH_ID = "user-regional-bishop-north"
OUTSIDER_ID = "user-outsider"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


async def _seed(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    region_north_id = generate_id()
    region_south_id = generate_id()
    church_a1 = generate_id()
    church_a2 = generate_id()
    church_b1 = generate_id()
    pastor_type_id = generate_id()
    diacon_type_id = generate_id()
    group_id = generate_id()

    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin"),
            UserDB(id=PASTOR_A1_ID, email="pastor-a1@example.com", name="Pastor A1"),
            UserDB(
                id=BISHOP_NORTH_ID,
                email="bishop-north@example.com",
                name="Bishop North",
            ),
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            RegionDB(
                id=region_north_id,
                community_id=community_id,
                name="Polnoc",
                slug="polnoc",
                created_at=now,
            ),
            RegionDB(
                id=region_south_id,
                community_id=community_id,
                name="Poludnie",
                slug="poludnie",
                created_at=now,
            ),
            ChurchDB(
                id=church_a1,
                community_id=community_id,
                region_id=region_north_id,
                tenant_id=church_a1,
                name="Zbor A1",
                visibility="public",
                created_at=now,
            ),
            ChurchDB(
                id=church_a2,
                community_id=community_id,
                region_id=region_north_id,
                tenant_id=church_a2,
                name="Zbor A2",
                visibility="public",
                created_at=now,
            ),
            ChurchDB(
                id=church_b1,
                community_id=community_id,
                region_id=region_south_id,
                tenant_id=church_b1,
                name="Zbor B1",
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
            ServiceTypeDB(
                id=diacon_type_id,
                slug="diacon",
                name="Diakon",
                scope_type="church",
                sort_order=2,
            ),
        ]
    )
    await session.flush()

    roles = await ensure_acl_roles(session)
    session.add_all(
        [
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=PASTOR_A1_ID,
                role_id=roles["pastor"].id,
                scope_type="church",
                scope_id=church_a1,
                created_at=now,
            ),
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=BISHOP_NORTH_ID,
                role_id=roles["regional_bishop"].id,
                scope_type="region",
                scope_id=region_north_id,
                created_at=now,
            ),
        ]
    )

    # Persons: pastor at A1, diacon at A2 (both region North), pastor at B1 (region South).
    person_a1_pastor = PersonDB(id=generate_id(), first_name="Jan", last_name="A1", email="jan.a1@example.com")
    person_a2_diacon = PersonDB(id=generate_id(), first_name="Ola", last_name="A2", email="ola.a2@example.com")
    person_b1_pastor = PersonDB(id=generate_id(), first_name="Bea", last_name="B1", email="bea.b1@example.com")
    person_no_email = PersonDB(id=generate_id(), first_name="Nick", last_name="NoEmail", email=None)
    session.add_all([person_a1_pastor, person_a2_diacon, person_b1_pastor, person_no_email])
    await session.flush()

    session.add_all(
        [
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_a1_pastor.id,
                service_type_id=pastor_type_id,
                scope_type="church",
                scope_id=church_a1,
                card_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                created_at=now,
            ),
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_a2_diacon.id,
                service_type_id=diacon_type_id,
                scope_type="church",
                scope_id=church_a2,
                card_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                created_at=now,
            ),
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_b1_pastor.id,
                service_type_id=pastor_type_id,
                scope_type="church",
                scope_id=church_b1,
                card_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                created_at=now,
            ),
        ]
    )

    session.add(
        PeopleGroupDB(
            id=group_id,
            name="Prezydium",
            slug="prezydium",
            visibility="authenticated",
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    session.add(
        PeopleGroupMembershipDB(
            id=generate_id(),
            group_id=group_id,
            person_id=person_b1_pastor.id,
            joined_at=now,
        )
    )

    await session.commit()

    return {
        "region_north": region_north_id,
        "region_south": region_south_id,
        "church_a1": church_a1,
        "church_a2": church_a2,
        "church_b1": church_b1,
        "pastor_type": pastor_type_id,
        "diacon_type": diacon_type_id,
        "group": group_id,
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

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        ids = await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, ids, login

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_outsider_denied(ctx) -> None:
    client, _, login = ctx
    login(_api_user(OUTSIDER_ID))

    filters = await client.get("/api/people-directory/filters")
    export = await client.get("/api/people-directory/export")

    assert filters.status_code == 403
    assert export.status_code == 403


@pytest.mark.asyncio
async def test_pastor_sees_only_own_church(ctx) -> None:
    client, _, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.get("/api/people-directory/export")

    assert response.status_code == 200
    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {"jan.a1@example.com"}


@pytest.mark.asyncio
async def test_regional_bishop_sees_whole_region_not_other_region(ctx) -> None:
    client, _, login = ctx
    login(_api_user(BISHOP_NORTH_ID))

    response = await client.get("/api/people-directory/export")

    assert response.status_code == 200
    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {"jan.a1@example.com", "ola.a2@example.com"}


@pytest.mark.asyncio
async def test_admin_sees_everyone_with_email(ctx) -> None:
    client, _, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get("/api/people-directory/export")

    assert response.status_code == 200
    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {
        "jan.a1@example.com",
        "ola.a2@example.com",
        "bea.b1@example.com",
    }


@pytest.mark.asyncio
async def test_admin_can_filter_by_region(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get(
        "/api/people-directory/export",
        params={"regionIds": ids["region_south"]},
    )

    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {"bea.b1@example.com"}


@pytest.mark.asyncio
async def test_region_and_role_filter_combine_on_same_assignment(ctx) -> None:
    """Region=North + role=Diakon must exclude the North pastor."""
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get(
        "/api/people-directory/export",
        params={"regionIds": ids["region_north"], "serviceTypeIds": ids["diacon_type"]},
    )

    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {"ola.a2@example.com"}


@pytest.mark.asyncio
async def test_group_filter(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get(
        "/api/people-directory/export",
        params={"groupIds": ids["group"]},
    )

    emails = {p["email"] for p in response.json()["persons"]}
    assert emails == {"bea.b1@example.com"}


@pytest.mark.asyncio
async def test_pastor_filters_persons_never_appears(ctx) -> None:
    """A pastor cannot use filters to reach outside their own church scope."""
    client, ids, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.get(
        "/api/people-directory/export",
        params={"regionIds": ids["region_south"]},
    )

    assert response.json()["persons"] == []


@pytest.mark.asyncio
async def test_filters_endpoint_scopes_regions(ctx) -> None:
    client, _, login = ctx

    login(_api_user(PASTOR_A1_ID))
    pastor_filters = await client.get("/api/people-directory/filters")
    pastor_regions = {r["id"] for r in pastor_filters.json()["regions"]}

    login(_api_user(ADMIN_ID, is_admin=True))
    admin_filters = await client.get("/api/people-directory/filters")
    admin_regions = {r["id"] for r in admin_filters.json()["regions"]}

    assert len(pastor_regions) == 1
    assert len(admin_regions) == 2
    assert pastor_regions.issubset(admin_regions)
