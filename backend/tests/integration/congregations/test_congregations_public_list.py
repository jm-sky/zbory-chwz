"""Public congregation list: geo fields, branches, and address-status filtering.

Covers `GET /api/congregations/detailed`, which backs the public list, its
country/province filters and the JSON/Markdown export.
"""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing"
)
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_POOL_SIZE", "1")
os.environ.setdefault("DATABASE_MAX_OVERFLOW", "0")

from app.common.id_utils import generate_id
from app.core.database import Base, get_db
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_optional_current_user
from app.modules.auth.models import User
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

OWNER_ID = "user-owner"
MEMBER_ID = "user-member"
WROCLAW = "church-wroclaw"
MARKTREDWITZ = "church-marktredwitz"
DRAFT = "church-draft"

# A church row shares its id with the tenant, so the tenant id is also the
# church id used as an assignment/branch scope.


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    service_type_id = generate_id()

    session.add_all(
        [
            UserDB(id=OWNER_ID, email="owner@example.com", name="Owner"),
            UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ServiceTypeDB(
                id=service_type_id,
                slug="pastor",
                name="Pastor",
                scope_type="church",
                sort_order=10,
            ),
        ]
    )

    churches = [
        (WROCLAW, "ZBÓR WE WROCŁAWIU", "Wrocław", "dolnoslaskie", "PL", "published"),
        (MARKTREDWITZ, "ZBÓR W MARKTREDWITZ", "Marktredwitz", None, "DE", "published"),
        (DRAFT, "ZBÓR ROBOCZY", "Gdańsk", "pomorskie", "PL", "draft"),
    ]

    for church_id, name, city, province, country, status in churches:
        session.add(
            TenantDB(
                id=church_id,
                name=name,
                status="published",
                owner_id=OWNER_ID,
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
                city=city,
                province=province,
                country=country,
                status=status,
                created_at=now,
                updated_at=now,
            )
        )

    session.add(
        CongregationServiceTimeDB(
            id=generate_id(),
            tenant_id=WROCLAW,
            day="niedziela",
            time="10:00",
            order=0,
            created_at=now,
        )
    )

    session.add_all(
        [
            BranchDB(
                id="branch-public",
                church_id=WROCLAW,
                name="Placówka Psie Pole",
                slug="psie-pole",
                visibility="public",
                created_at=now,
            ),
            BranchDB(
                id="branch-hidden",
                church_id=WROCLAW,
                name="Placówka Ukryta",
                slug="ukryta",
                visibility="hidden",
                created_at=now,
            ),
            # A branch of a congregation that is not published at all.
            BranchDB(
                id="branch-of-draft",
                church_id=DRAFT,
                name="Placówka Robocza",
                slug="robocza",
                visibility="public",
                created_at=now,
            ),
        ]
    )

    person = PersonDB(id=generate_id(), first_name="Jan", last_name="Kowalski")
    session.add(person)
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=person.id,
            service_type_id=service_type_id,
            scope_type="church",
            scope_id=WROCLAW,
            card_visibility="public",
            phone_visibility="public",
            email_visibility="authenticated",
            created_at=now,
        )
    )
    session.add(
        TenantMembershipDB(
            tenant_id=DRAFT,
            user_id=MEMBER_ID,
            role="member",
        )
    )
    await session.commit()


def _owner() -> User:
    return User(
        id=OWNER_ID,
        email="owner@example.com",
        name="Owner",
        isAdmin=False,
        isOwner=True,
        createdAt=datetime.now(UTC),
    )


def _member() -> User:
    return User(
        id=MEMBER_ID,
        email="member@example.com",
        name="Member",
        isAdmin=False,
        isOwner=False,
        createdAt=datetime.now(UTC),
    )


@pytest_asyncio.fixture
async def client():
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
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    await engine.dispose()


async def _detailed(client: AsyncClient) -> dict[str, dict]:
    response = await client.get("/api/congregations/detailed")
    assert response.status_code == 200
    return {item["name"]: item for item in response.json()["congregations"]}


@pytest.mark.asyncio
async def test_detailed_list_is_public(client) -> None:
    response = await client.get("/api/congregations/detailed")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_exposes_country_and_province(client) -> None:
    items = await _detailed(client)

    assert items["ZBÓR WE WROCŁAWIU"]["country"] == "PL"
    assert items["ZBÓR WE WROCŁAWIU"]["province"] == "dolnoslaskie"
    assert items["ZBÓR W MARKTREDWITZ"]["country"] == "DE"
    assert items["ZBÓR W MARKTREDWITZ"]["province"] is None


@pytest.mark.asyncio
async def test_unpublished_address_is_excluded(client) -> None:
    items = await _detailed(client)
    assert "ZBÓR ROBOCZY" not in items


@pytest.mark.asyncio
async def test_public_branch_is_listed_under_its_congregation(client) -> None:
    items = await _detailed(client)
    branch = items["Placówka Psie Pole"]

    assert branch["type"] == "branch"
    assert branch["parent_id"] == WROCLAW
    assert branch["parent_name"] == "ZBÓR WE WROCŁAWIU"
    # A branch has no address of its own; it inherits the congregation's, so
    # the country/province filters keep it next to its parent.
    assert branch["country"] == "PL"
    assert branch["province"] == "dolnoslaskie"


@pytest.mark.asyncio
async def test_hidden_branch_is_not_listed(client) -> None:
    items = await _detailed(client)
    assert "Placówka Ukryta" not in items


@pytest.mark.asyncio
async def test_branch_of_unpublished_congregation_is_not_listed(client) -> None:
    items = await _detailed(client)
    assert "Placówka Robocza" not in items


@pytest.mark.asyncio
async def test_congregation_keeps_its_service_times_and_contacts(client) -> None:
    items = await _detailed(client)
    church = items["ZBÓR WE WROCŁAWIU"]

    assert church["type"] == "church"
    assert church["service_times"] == [{"day": "niedziela", "time": "10:00"}]
    assert church["card_contacts"][0]["name"] == "Jan Kowalski"
    assert church["contact_name"] == "Jan Kowalski"
    # E-mail defaults to authenticated-only visibility.
    assert church["card_contacts"][0]["email"] is None


@pytest.mark.asyncio
async def test_draft_congregation_visible_for_owner(client) -> None:
    http_client = client
    app.dependency_overrides[get_optional_current_user] = _owner
    try:
        items = await _detailed(http_client)
        draft = items["ZBÓR ROBOCZY"]
        assert draft["status"] == "draft"
        assert draft["city"] == "Gdańsk"
    finally:
        app.dependency_overrides.pop(get_optional_current_user, None)


@pytest.mark.asyncio
async def test_draft_congregation_visible_for_member_of_that_tenant(client) -> None:
    http_client = client
    app.dependency_overrides[get_optional_current_user] = _member
    try:
        items = await _detailed(http_client)
        assert "ZBÓR ROBOCZY" in items
        assert items["ZBÓR ROBOCZY"]["status"] == "draft"
    finally:
        app.dependency_overrides.pop(get_optional_current_user, None)
