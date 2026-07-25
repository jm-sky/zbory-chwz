"""Authorization tests for tenant-scoped congregation endpoints.

Regression cover for:
- SEC-1: /congregations/* had no access check beyond "is logged in"
- SEC-2: suggestedRole let any editor grant themselves an elevated ACL role
- BUG-1: cross-church PATCH mutated the target before the scope check ran
"""

import os
from datetime import UTC, datetime

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
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import (
    ChurchDB,
    CommunityDB,
    PersonDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

OUTSIDER_ID = "user-outsider"
MEMBER_ID = "user-member"
CHURCH_A = "church-a"
CHURCH_B = "church-b"


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
    service_type_id = generate_id()
    pastor_service_type_id = generate_id()

    session.add_all(
        [
            UserDB(id=OUTSIDER_ID, email="outsider@example.com", name="Outsider"),
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ServiceTypeDB(
                id=service_type_id,
                slug="diacon",
                name="Diakon",
                scope_type="church",
                sort_order=10,
            ),
            ServiceTypeDB(
                id=pastor_service_type_id,
                slug="pastor",
                name="Pastor",
                scope_type="church",
                sort_order=5,
            ),
        ]
    )

    for church_id, name in ((CHURCH_A, "Zbor A"), (CHURCH_B, "Zbor B")):
        session.add(
            TenantDB(
                id=church_id,
                name=name,
                status="published",
                owner_id=MEMBER_ID,
                created_at=now,
            )
        )
        session.add(
            ChurchDB(
                id=church_id,
                community_id=community_id,
                tenant_id=church_id,
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

    # The member belongs to church A only.
    session.add(TenantMembershipDB(tenant_id=CHURCH_A, user_id=MEMBER_ID, role="member"))

    roles = await ensure_acl_roles(session)
    pastor_role = roles["pastor"]
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=MEMBER_ID,
            role_id=pastor_role.id,
            scope_type="church",
            scope_id=CHURCH_A,
        )
    )

    # An assignment living in church B — the cross-church PATCH target.
    person_b = PersonDB(id=generate_id(), first_name="Bogdan", last_name="B")
    session.add(person_b)
    await session.flush()

    assignment_b = ServiceAssignmentDB(
        id=generate_id(),
        person_id=person_b.id,
        service_type_id=service_type_id,
        scope_type="church",
        scope_id=CHURCH_B,
        profile_visibility="public",
        phone_visibility="public",
        email_visibility="authenticated",
        created_at=now,
    )
    session.add(assignment_b)
    await session.commit()

    return {
        "assignment_b": assignment_b.id,
        "person_b": person_b.id,
        "service_type": service_type_id,
        "pastor_service_type": pastor_service_type_id,
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

        yield client, ids, login, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_outsider_cannot_read_congregation_address(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(OUTSIDER_ID))

    response = await client.get(f"/api/congregations/{CHURCH_A}/address")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_outsider_cannot_overwrite_congregation_address(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(OUTSIDER_ID))

    # A valid payload, so the request is rejected by the access check rather
    # than by body validation.
    response = await client.post(
        f"/api/congregations/{CHURCH_A}/address",
        json={"city": "Hacked", "country": "PL"},
    )

    assert response.status_code == 403

    login(_api_user(MEMBER_ID))
    stored = await client.get(f"/api/congregations/{CHURCH_A}/address")
    assert stored.json()["city"] == "Zbor A"


@pytest.mark.asyncio
async def test_member_reads_own_congregation(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.get(f"/api/congregations/{CHURCH_A}/address")

    assert response.status_code == 200
    assert response.json()["city"] == "Zbor A"


@pytest.mark.asyncio
async def test_member_cannot_reach_other_congregation(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.get(f"/api/congregations/{CHURCH_B}/address")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_reaches_any_congregation(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user("user-admin", is_admin=True))

    response = await client.get(f"/api/congregations/{CHURCH_B}/address")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_member_cannot_patch_assignment_of_other_church(ctx) -> None:
    client, ids, login, session_factory = ctx
    login(_api_user(MEMBER_ID))

    response = await client.patch(
        f"/api/churches/{CHURCH_A}/service-assignments/{ids['assignment_b']}",
        json={"firstName": "Overwritten"},
    )

    assert response.status_code == 404
    async with session_factory() as session:
        person = await session.get(PersonDB, ids["person_b"])
        assert person is not None
        assert person.first_name == "Bogdan"


@pytest.mark.asyncio
async def test_member_cannot_grant_bishop_role(ctx) -> None:
    client, ids, login, session_factory = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/churches/{CHURCH_A}/service-assignments",
        json={
            "firstName": "Member",
            "email": "member@example.com",
            "serviceTypeId": ids["service_type"],
            "createAccount": True,
            "suggestedRole": "bishop",
        },
    )

    assert response.status_code == 403
    async with session_factory() as session:
        result = await session.get(UserRoleAssignmentDB, MEMBER_ID)
        assert result is None


@pytest.mark.asyncio
async def test_admin_may_grant_bishop_role(ctx) -> None:
    client, ids, login, _ = ctx
    login(_api_user("user-admin", is_admin=True))

    response = await client.post(
        f"/api/churches/{CHURCH_A}/service-assignments",
        json={
            "firstName": "Roman",
            "lastName": "Jawdyk",
            "email": "roman@example.com",
            "serviceTypeId": ids["service_type"],
            "createAccount": True,
            "suggestedRole": "bishop",
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_pastor_without_create_account_does_not_require_email(ctx) -> None:
    client, ids, login, session_factory = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/churches/{CHURCH_A}/service-assignments",
        json={
            "firstName": "Jan",
            "lastName": "Kowalski",
            "serviceTypeId": ids["pastor_service_type"],
            "createAccount": False,
        },
    )

    assert response.status_code == 201
    async with session_factory() as session:
        # first_name is encrypted at rest (non-deterministic ciphertext), so
        # an equality filter can't run in SQL — decrypt-then-filter instead.
        persons = (await session.scalars(select(PersonDB))).all()
        person = next((p for p in persons if p.first_name == "Jan"), None)
        assert person is not None
        assert person.email is None
        assert person.user_id is None


@pytest.mark.asyncio
async def test_pastor_with_create_account_still_requires_email(ctx) -> None:
    client, ids, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post(
        f"/api/churches/{CHURCH_A}/service-assignments",
        json={
            "firstName": "Piotr",
            "lastName": "Nowak",
            "serviceTypeId": ids["pastor_service_type"],
            "createAccount": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email required to create user account"


@pytest.mark.asyncio
async def test_list_service_assignments_sorted_by_sort_order(ctx) -> None:
    client, ids, login, session_factory = ctx
    login(_api_user(MEMBER_ID))

    async with session_factory() as session:
        person_first = PersonDB(id=generate_id(), first_name="First", last_name="Person")
        person_second = PersonDB(id=generate_id(), first_name="Second", last_name="Person")
        session.add_all([person_first, person_second])
        await session.flush()
        session.add(
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_second.id,
                service_type_id=ids["service_type"],
                scope_type="church",
                scope_id=CHURCH_A,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="public",
                sort_order=1,
            )
        )
        session.add(
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person_first.id,
                service_type_id=ids["service_type"],
                scope_type="church",
                scope_id=CHURCH_A,
                profile_visibility="public",
                phone_visibility="public",
                email_visibility="public",
                sort_order=0,
            )
        )
        await session.commit()

    response = await client.get(f"/api/churches/{CHURCH_A}/service-assignments")
    assert response.status_code == 200
    names = [" ".join(p for p in (a["person"]["firstName"], a["person"]["lastName"]) if p) for a in response.json()]
    assert names[0] == "First Person"
    assert names[1] == "Second Person"


@pytest.mark.asyncio
async def test_member_can_patch_own_congregation(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.patch(
        f"/api/congregations/{CHURCH_A}",
        json={"name": "Zbor A Renamed", "description": "Nowy opis"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Zbor A Renamed"
    assert body["description"] == "Nowy opis"


@pytest.mark.asyncio
async def test_member_cannot_patch_other_congregation(ctx) -> None:
    client, _, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.patch(
        f"/api/congregations/{CHURCH_B}",
        json={"name": "Hacked"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("target_status", ["draft", "published", "published_unverified", "need_verification"])
@pytest.mark.asyncio
async def test_member_can_set_any_status_on_own_congregation(ctx, target_status: str) -> None:
    client, _, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.patch(
        f"/api/congregations/{CHURCH_A}",
        json={"status": target_status},
    )

    assert response.status_code == 200
    assert response.json()["status"] == target_status


@pytest.mark.asyncio
async def test_patch_service_assignment_sort_order(ctx) -> None:
    client, ids, login, _ = ctx
    login(_api_user(MEMBER_ID))

    create_response = await client.post(
        f"/api/churches/{CHURCH_A}/service-assignments",
        json={
            "firstName": "Sort",
            "lastName": "Test",
            "serviceTypeId": ids["service_type"],
        },
    )
    assert create_response.status_code == 201
    assignment_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/churches/{CHURCH_A}/service-assignments/{assignment_id}",
        json={"sortOrder": 5},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["sortOrder"] == 5
