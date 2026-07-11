"""Integration tests for the person browser (list/detail/edit/merge).

Covers the 2026-07-11 decisions: same ACL scope as the email export, edit is
in-place on `persons` (no delete), and merging moves service_assignments and
active group memberships from the duplicate onto the survivor, skipping any
group the survivor already belongs to.
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

ADMIN_ID = "user-admin-pb"
PASTOR_A1_ID = "user-pastor-a1-pb"
OUTSIDER_ID = "user-outsider-pb"


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
    church_b1 = generate_id()
    pastor_type_id = generate_id()
    group_id = generate_id()

    session.add_all(
        [
            UserDB(id=ADMIN_ID, email="admin-pb@example.com", name="Admin"),
            UserDB(id=PASTOR_A1_ID, email="pastor-a1-pb@example.com", name="Pastor A1"),
            UserDB(id=OUTSIDER_ID, email="outsider-pb@example.com", name="Outsider"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz-pb", created_at=now),
            RegionDB(
                id=region_north_id,
                community_id=community_id,
                name="Polnoc",
                slug="polnoc-pb",
                created_at=now,
            ),
            RegionDB(
                id=region_south_id,
                community_id=community_id,
                name="Poludnie",
                slug="poludnie-pb",
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
        ]
    )
    await session.flush()

    roles = await ensure_acl_roles(session)
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=PASTOR_A1_ID,
            role_id=roles["pastor"].id,
            scope_type="church",
            scope_id=church_a1,
            created_at=now,
        )
    )

    # Two duplicate records for "the same" person: one in A1 (in-scope for the pastor),
    # one in B1 (out of scope). A third, unrelated person also lives in B1.
    person_a1 = PersonDB(
        id=generate_id(),
        first_name="Jan",
        last_name="Kowalski",
        email="jan.a1@example.com",
    )
    person_b1_duplicate = PersonDB(id=generate_id(), first_name="Janek", last_name="Kowalski", phone="+48600000000")
    person_b1_other = PersonDB(id=generate_id(), first_name="Inna", last_name="Osoba")
    session.add_all([person_a1, person_b1_duplicate, person_b1_other])
    await session.flush()

    session.add_all(
        [
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_a1.id,
                service_type_id=pastor_type_id,
                scope_type="church",
                scope_id=church_a1,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                created_at=now,
            ),
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_b1_duplicate.id,
                service_type_id=pastor_type_id,
                scope_type="church",
                scope_id=church_b1,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="hidden",
                created_at=now,
            ),
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_b1_other.id,
                service_type_id=pastor_type_id,
                scope_type="church",
                scope_id=church_b1,
                profile_visibility="public",
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
            slug="prezydium-pb",
            visibility="authenticated",
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    # Both "duplicate" records are already in the same group — merging must not
    # create two active memberships for the survivor.
    session.add_all(
        [
            PeopleGroupMembershipDB(
                id=generate_id(),
                group_id=group_id,
                person_id=person_a1.id,
                joined_at=now,
            ),
            PeopleGroupMembershipDB(
                id=generate_id(),
                group_id=group_id,
                person_id=person_b1_duplicate.id,
                joined_at=now,
            ),
        ]
    )

    await session.commit()

    return {
        "church_a1": church_a1,
        "church_b1": church_b1,
        "person_a1": person_a1.id,
        "person_b1_duplicate": person_b1_duplicate.id,
        "person_b1_other": person_b1_other.id,
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
async def test_pastor_list_scoped_to_own_church(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.get("/api/people-directory/persons")

    assert response.status_code == 200
    names = {p["firstName"] for p in response.json()["persons"]}
    assert names == {"Jan"}


@pytest.mark.asyncio
async def test_admin_list_includes_everyone(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get("/api/people-directory/persons")

    names = {p["firstName"] for p in response.json()["persons"]}
    assert names == {"Jan", "Janek", "Inna"}


@pytest.mark.asyncio
async def test_person_detail_includes_affiliations(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get(f"/api/people-directory/persons/{ids['person_a1']}")

    assert response.status_code == 200
    body = response.json()
    kinds = {(a["kind"], a["label"]) for a in body["affiliations"]}
    assert ("service", "Pastor") in kinds
    assert ("group", "Prezydium") in kinds


@pytest.mark.asyncio
async def test_pastor_cannot_view_person_outside_scope(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.get(f"/api/people-directory/persons/{ids['person_b1_other']}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_person(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.patch(
        f"/api/people-directory/persons/{ids['person_a1']}",
        json={"phone": "+48111222333"},
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "+48111222333"
    assert response.json()["firstName"] == "Jan"  # untouched fields survive


@pytest.mark.asyncio
async def test_pastor_cannot_edit_person_outside_scope(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.patch(
        f"/api/people-directory/persons/{ids['person_b1_other']}",
        json={"firstName": "Hacked"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_merge_moves_assignment_and_dedupes_group_membership(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/people-directory/persons/merge",
        json={
            "keepPersonId": ids["person_a1"],
            "mergePersonId": ids["person_b1_duplicate"],
        },
    )

    assert response.status_code == 200
    survivor = response.json()
    assert survivor["id"] == ids["person_a1"]
    assert survivor["phone"] == "+48600000000"  # picked up from the merged record

    # The merged person is gone.
    gone = await client.get(f"/api/people-directory/persons/{ids['person_b1_duplicate']}")
    assert gone.status_code == 404

    # Survivor now has both service assignments (A1 + B1) but only one group membership.
    detail = await client.get(f"/api/people-directory/persons/{ids['person_a1']}")
    affiliations = detail.json()["affiliations"]
    service_count = sum(1 for a in affiliations if a["kind"] == "service")
    group_count = sum(1 for a in affiliations if a["kind"] == "group")
    assert service_count == 2
    assert group_count == 1


@pytest.mark.asyncio
async def test_cannot_merge_person_into_themself(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/people-directory/persons/merge",
        json={"keepPersonId": ids["person_a1"], "mergePersonId": ids["person_a1"]},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pastor_cannot_merge_across_scope(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(PASTOR_A1_ID))

    response = await client.post(
        "/api/people-directory/persons/merge",
        json={
            "keepPersonId": ids["person_a1"],
            "mergePersonId": ids["person_b1_other"],
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_outsider_denied(ctx) -> None:
    client, ids, login = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.get("/api/people-directory/persons")

    assert response.status_code == 403
