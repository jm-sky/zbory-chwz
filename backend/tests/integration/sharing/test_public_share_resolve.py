"""Integration tests for GET /api/share/{token} (anonymous share-link resolution)."""

import os
import secrets
from datetime import UTC, datetime, timedelta

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
from app.modules.churches.db_models import (
    ChurchDB,
    CommunityDB,
    PersonDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.sharing.db_models import ShareLinkDB
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
from main import app

TENANT_ID = "church-shared"
OWNER_ID = "user-owner"

PUBLIC_TOKEN = secrets.token_urlsafe(32)
AUTHENTICATED_TOKEN = secrets.token_urlsafe(32)
PASTORS_TOKEN = secrets.token_urlsafe(32)
EXPIRED_TOKEN = secrets.token_urlsafe(32)
REVOKED_TOKEN = secrets.token_urlsafe(32)
ALL_CONGREGATIONS_TOKEN = secrets.token_urlsafe(32)


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    community_id = generate_id()
    diacon_type_id = generate_id()

    session.add_all(
        [
            UserDB(id=OWNER_ID, email="owner@example.com", name="Owner"),
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ServiceTypeDB(
                id=diacon_type_id,
                slug="diacon",
                name="Diakon",
                scope_type="church",
                sort_order=10,
            ),
        ]
    )
    session.add(
        TenantDB(
            id=TENANT_ID,
            name="Zbor Testowy",
            status="published",
            owner_id=OWNER_ID,
            created_at=now,
        )
    )
    session.add(
        ChurchDB(
            id=TENANT_ID,
            community_id=community_id,
            tenant_id=TENANT_ID,
            name="Zbor Testowy",
            visibility="public",
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=TENANT_ID,
            city="Warszawa",
            street="Testowa 1",
            country="PL",
            status="published",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(TenantMembershipDB(tenant_id=TENANT_ID, user_id=OWNER_ID, role="owner"))

    contact_person = PersonDB(
        id=generate_id(),
        first_name="Anna",
        last_name="Nowak",
        phone="+48222222222",
        email="anna@example.com",
    )
    session.add(contact_person)
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=contact_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=TENANT_ID,
            profile_visibility="public",
            phone_visibility="public",
            email_visibility="authenticated",
            created_at=now,
        )
    )

    bishop_person = PersonDB(
        id=generate_id(),
        first_name="Piotr",
        last_name="Biskup",
        phone="+48333333333",
        email="piotr@example.com",
    )
    session.add(bishop_person)
    await session.flush()

    session.add(
        ServiceAssignmentDB(
            id=generate_id(),
            person_id=bishop_person.id,
            service_type_id=diacon_type_id,
            scope_type="church",
            scope_id=TENANT_ID,
            profile_visibility="pastors",
            phone_visibility="pastors",
            email_visibility="pastors",
            created_at=now,
        )
    )

    session.add_all(
        [
            ShareLinkDB(
                id=generate_id(),
                token=PUBLIC_TOKEN,
                tenant_id=TENANT_ID,
                created_by_user_id=OWNER_ID,
                visibility_level="public",
                expires_at=now + timedelta(days=7),
            ),
            ShareLinkDB(
                id=generate_id(),
                token=AUTHENTICATED_TOKEN,
                tenant_id=TENANT_ID,
                created_by_user_id=OWNER_ID,
                visibility_level="authenticated",
                expires_at=now + timedelta(days=7),
            ),
            ShareLinkDB(
                id=generate_id(),
                token=PASTORS_TOKEN,
                tenant_id=TENANT_ID,
                created_by_user_id=OWNER_ID,
                visibility_level="pastors",
                expires_at=now + timedelta(days=7),
            ),
            ShareLinkDB(
                id=generate_id(),
                token=EXPIRED_TOKEN,
                tenant_id=TENANT_ID,
                created_by_user_id=OWNER_ID,
                visibility_level="public",
                expires_at=now - timedelta(days=1),
            ),
            ShareLinkDB(
                id=generate_id(),
                token=REVOKED_TOKEN,
                tenant_id=TENANT_ID,
                created_by_user_id=OWNER_ID,
                visibility_level="public",
                expires_at=now + timedelta(days=7),
                revoked_at=now,
            ),
            ShareLinkDB(
                id=generate_id(),
                token=ALL_CONGREGATIONS_TOKEN,
                tenant_id=None,
                created_by_user_id=OWNER_ID,
                visibility_level="public",
                expires_at=now + timedelta(days=7),
            ),
        ]
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
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_level_link_hides_authenticated_only_fields(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{PUBLIC_TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "congregation"
    data = body["congregation"]
    assert data["name"] == "Zbor Testowy"
    contact = next(c for c in data["card_contacts"] if c["name"] == "Anna Nowak")
    assert contact["phone"] == "+48222222222"
    # email_visibility is "authenticated" -> hidden at the public grant level
    assert contact["email"] is None
    assert data["canManage"] is False
    assert data["role"] is None
    assert data.get("hidden_contacts", []) == []


@pytest.mark.asyncio
async def test_authenticated_level_link_reveals_authenticated_fields(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{AUTHENTICATED_TOKEN}")

    assert response.status_code == 200
    data = response.json()["congregation"]
    contact = next(c for c in data["card_contacts"] if c["name"] == "Anna Nowak")
    assert contact["email"] == "anna@example.com"
    assert data["canManage"] is False
    # profile_visibility="pastors" -> hidden at the authenticated grant level
    assert all(c["name"] != "Piotr Biskup" for c in data["card_contacts"])


@pytest.mark.asyncio
async def test_pastors_level_link_reveals_pastors_only_contact(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{PASTORS_TOKEN}")

    assert response.status_code == 200
    data = response.json()["congregation"]
    contact = next(c for c in data["card_contacts"] if c["name"] == "Piotr Biskup")
    assert contact["phone"] == "+48333333333"
    assert contact["email"] == "piotr@example.com"
    # Still strictly read-only: no membership or manage rights granted.
    assert data["canManage"] is False
    assert data["role"] is None
    assert data.get("hidden_contacts", []) == []


@pytest.mark.asyncio
async def test_all_congregations_link_resolves_to_published_list(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{ALL_CONGREGATIONS_TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "congregations"
    assert body["congregation"] is None
    ids = [congregation["id"] for congregation in body["congregations"]]
    assert TENANT_ID in ids


@pytest.mark.asyncio
async def test_expired_token_returns_404(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{EXPIRED_TOKEN}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoked_token_returns_404(ctx) -> None:
    client, _ = ctx

    response = await client.get(f"/api/share/{REVOKED_TOKEN}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_token_returns_404(ctx) -> None:
    client, _ = ctx

    response = await client.get("/api/share/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resolving_updates_last_used_at(ctx) -> None:
    client, session_factory = ctx

    response = await client.get(f"/api/share/{PUBLIC_TOKEN}")
    assert response.status_code == 200

    async with session_factory() as session:
        result = await session.execute(select(ShareLinkDB).where(ShareLinkDB.token == PUBLIC_TOKEN))
        share_link = result.scalar_one()
        assert share_link.last_used_at is not None
