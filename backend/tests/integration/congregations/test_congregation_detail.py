"""Integration tests for GET /api/congregations/{tenant_id}/detail."""

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
from app.modules.auth.dependencies import get_optional_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import RoleDB, UserRoleAssignmentDB
from app.modules.churches.db_models import (
    BranchDB,
    ChurchDB,
    CommunityDB,
    PersonDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.congregations.db_models import (
    CongregationAddressDB,
    CongregationServiceTimeDB,
)
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

PUBLISHED_ID = "church-published"
DRAFT_ID = "church-draft"
MEMBER_ID = "user-member"
PASTOR_ID = "user-pastor"


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
    owner_id = generate_id()
    diacon_type_id = generate_id()
    pastor_type_id = generate_id()

    session.add_all(
        [
            UserDB(id=owner_id, email="owner@example.com", name="Owner"),
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            UserDB(id=PASTOR_ID, email="pastor@example.com", name="Pastor"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ServiceTypeDB(
                id=diacon_type_id,
                slug="diacon",
                name="Diakon",
                scope_type="church",
                sort_order=10,
            ),
            ServiceTypeDB(
                id=pastor_type_id,
                slug="pastor",
                name="Pastor",
                scope_type="church",
                sort_order=5,
            ),
        ]
    )

    session.add(
        TenantDB(
            id=PUBLISHED_ID,
            name="Zbor Testowy",
            description="Opis",
            status="published",
            owner_id=owner_id,
            created_at=now,
        )
    )
    session.add(
        ChurchDB(
            id=PUBLISHED_ID,
            community_id=community_id,
            tenant_id=PUBLISHED_ID,
            name="Zbor Testowy",
            visibility="public",
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=PUBLISHED_ID,
            city="Warszawa",
            street="Testowa 1",
            postal_code="00-001",
            country="PL",
            status="published",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        CongregationServiceTimeDB(
            id=generate_id(),
            tenant_id=PUBLISHED_ID,
            day="niedziela",
            time="11:00",
            order=0,
            created_at=now,
        )
    )
    session.add(TenantMembershipDB(tenant_id=PUBLISHED_ID, user_id=MEMBER_ID, role="member"))

    session.add(
        TenantDB(
            id=DRAFT_ID,
            name="Zbor Draft",
            status="draft",
            owner_id=owner_id,
            created_at=now,
        )
    )
    session.add(
        ChurchDB(
            id=DRAFT_ID,
            community_id=community_id,
            tenant_id=DRAFT_ID,
            name="Zbor Draft",
            visibility="hidden",
            created_at=now,
        )
    )

    diacon_person = PersonDB(
        id=generate_id(),
        first_name="Anna",
        last_name="Nowak",
        phone="+48222222222",
        email="anna@example.com",
    )
    pastor_person = PersonDB(
        id=generate_id(),
        first_name="Jan",
        last_name="Kowalski",
        phone="+48111111111",
        email="jan@example.com",
    )
    hidden_person = PersonDB(
        id=generate_id(),
        first_name="Hidden",
        last_name="Person",
        phone="+48333333333",
        email="hidden@example.com",
    )
    session.add_all([diacon_person, pastor_person, hidden_person])
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=diacon_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=PUBLISHED_ID,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="authenticated",
            created_at=now,
        )
    )
    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=pastor_person.id,
            service_type_id=pastor_type_id,
            scope_type="church",
            scope_id=PUBLISHED_ID,
            card_visibility="pastors",
            phone_visibility="pastors",
            email_visibility="pastors",
            created_at=now,
        )
    )
    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=hidden_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=PUBLISHED_ID,
            card_visibility="hidden",
            phone_visibility="public",
            email_visibility="public",
            created_at=now,
        )
    )

    session.add(
        BranchDB(
            id=generate_id(),
            church_id=PUBLISHED_ID,
            name="Placowka Publiczna",
            slug="placowka-publiczna",
            visibility="public",
        )
    )
    session.add(
        BranchDB(
            id=generate_id(),
            church_id=PUBLISHED_ID,
            name="Placowka Ukryta",
            slug="placowka-ukryta",
            visibility="hidden",
        )
    )

    pastor_role = RoleDB(id=generate_id(), name="pastor", scope_type="church")
    session.add(pastor_role)
    await session.flush()
    session.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=PASTOR_ID,
            role_id=pastor_role.id,
            scope_type="church",
            scope_id=PUBLISHED_ID,
        )
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

        def login(user: User | None) -> None:
            app.dependency_overrides[get_optional_current_user] = lambda: user

        yield client, login

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_congregation_returns_404(ctx) -> None:
    client, login = ctx
    login(None)

    response = await client.get("/api/congregations/does-not-exist/detail")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_draft_congregation_hidden_from_anonymous(ctx) -> None:
    client, login = ctx
    login(None)

    response = await client.get(f"/api/congregations/{DRAFT_ID}/detail")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_draft_congregation_visible_to_member_or_admin(ctx) -> None:
    client, login = ctx
    login(_api_user("user-admin", is_admin=True))

    response = await client.get(f"/api/congregations/{DRAFT_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
    assert data["canManage"] is True


@pytest.mark.asyncio
async def test_anonymous_sees_only_public_fields(ctx) -> None:
    client, login = ctx
    login(None)

    response = await client.get(f"/api/congregations/{PUBLISHED_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Zbor Testowy"
    assert data["city"] == "Warszawa"
    assert len(data["service_times"]) == 1

    # Every assignment is listed; card_visibility does not apply on the detail page.
    contact_names = {contact["name"] for contact in data["card_contacts"]}
    assert contact_names == {"Anna Nowak", "Jan Kowalski", "Hidden Person"}
    anna = next(c for c in data["card_contacts"] if c["name"] == "Anna Nowak")
    assert anna["phone"] == "+48222222222"
    # email_visibility is "authenticated" -> hidden from anonymous viewers
    assert anna["email"] is None
    jan = next(c for c in data["card_contacts"] if c["name"] == "Jan Kowalski")
    assert jan["phone"] is None
    assert jan["email"] is None
    hidden = next(c for c in data["card_contacts"] if c["name"] == "Hidden Person")
    assert hidden["phone"] == "+48333333333"
    assert hidden["email"] == "hidden@example.com"

    branch_names = {branch["name"] for branch in data["branches"]}
    assert branch_names == {"Placowka Publiczna"}

    assert data["role"] is None
    assert data["canManage"] is False


@pytest.mark.asyncio
async def test_authenticated_non_member_sees_authenticated_fields(ctx) -> None:
    client, login = ctx
    login(_api_user("user-random"))

    response = await client.get(f"/api/congregations/{PUBLISHED_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    contact = next(c for c in data["card_contacts"] if c["name"] == "Anna Nowak")
    assert contact["email"] == "anna@example.com"

    # All assignments are listed; pastors-only contact fields stay hidden.
    contact_names = {contact["name"] for contact in data["card_contacts"]}
    assert contact_names == {"Anna Nowak", "Jan Kowalski", "Hidden Person"}
    jan = next(c for c in data["card_contacts"] if c["name"] == "Jan Kowalski")
    assert jan["phone"] is None
    assert jan["email"] is None

    assert data["role"] is None
    assert data["canManage"] is False


@pytest.mark.asyncio
async def test_member_without_pastoral_access_sees_all_assignments(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.get(f"/api/congregations/{PUBLISHED_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["canManage"] is True

    contact_names = {contact["name"] for contact in data["card_contacts"]}
    assert contact_names == {"Anna Nowak", "Jan Kowalski", "Hidden Person"}

    branch_names = {branch["name"] for branch in data["branches"]}
    assert branch_names == {"Placowka Publiczna"}


@pytest.mark.asyncio
async def test_pastoral_user_sees_pastors_only_fields(ctx) -> None:
    client, login = ctx
    login(_api_user(PASTOR_ID))

    response = await client.get(f"/api/congregations/{PUBLISHED_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    contact_names = {contact["name"] for contact in data["card_contacts"]}
    assert contact_names == {"Anna Nowak", "Jan Kowalski", "Hidden Person"}
    pastor_contact = next(c for c in data["card_contacts"] if c["name"] == "Jan Kowalski")
    assert pastor_contact["phone"] == "+48111111111"
    assert pastor_contact["email"] == "jan@example.com"


@pytest.mark.asyncio
async def test_member_gets_role_and_can_manage(ctx) -> None:
    client, login = ctx
    login(_api_user(MEMBER_ID))

    response = await client.get(f"/api/congregations/{PUBLISHED_ID}/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "member"
    assert data["canManage"] is True
