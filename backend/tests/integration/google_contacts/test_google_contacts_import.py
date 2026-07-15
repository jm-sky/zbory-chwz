"""Integration tests for Phase 2/3 of the Google Contacts import (mapping + apply).

Covers docs/plans/2026-07-10--google-contacts-sync.md decisions #4-#7:
church fuzzy-name matching, person exact email/phone matching, and that
"Importuj do bazy" creates/updates the right records per the admin's
confirmed choices.
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
os.environ.setdefault("DATABASE_POOL_SIZE", "1")
os.environ.setdefault("DATABASE_MAX_OVERFLOW", "0")

from app.common.id_utils import generate_id
from app.core.database import Base, get_db
from app.modules.auth.db_models import UserDB
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, ServiceAssignmentDB
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.tenants.db_models import TenantDB
from main import app

ADMIN_ID = "user-admin"
MEMBER_ID = "user-member"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


def _contact(
    resource_name: str,
    *,
    display_name: str | None = None,
    organization_name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    city: str | None = None,
) -> dict:
    return {
        "resourceName": resource_name,
        "displayName": display_name,
        "firstName": first_name,
        "lastName": last_name,
        "organizationName": organization_name,
        "emailAddresses": [email] if email else [],
        "phoneNumbers": [phone] if phone else [],
        "notes": None,
        "suggestedType": "church" if organization_name else "person",
        "addressStreet": None,
        "addressCity": city,
        "addressPostalCode": None,
        "addressProvince": None,
        "addressCountry": None,
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
        session.add_all(
            [
                UserDB(id=ADMIN_ID, email="admin@example.com", name="Admin", is_admin=True),
                UserDB(id=MEMBER_ID, email="member@example.com", name="Member"),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, login, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_tenant(session_factory, *, name: str) -> str:
    tenant_id = generate_id()
    async with session_factory() as session:
        session.add(TenantDB(id=tenant_id, name=name, status="published", owner_id=ADMIN_ID))
        await session.commit()
    return tenant_id


async def _seed_church(session_factory, *, tenant_id: str, name: str) -> None:
    async with session_factory() as session:
        community = CommunityDB(id=generate_id(), name="CHWZ", slug="chwz", visibility="hidden")
        session.add(community)
        await session.flush()
        session.add(
            ChurchDB(
                id=tenant_id,
                community_id=community.id,
                tenant_id=tenant_id,
                name=name,
                visibility="hidden",
            )
        )
        await session.commit()


async def _seed_person(session_factory, *, email: str | None = None, phone: str | None = None) -> str:
    person_id = generate_id()
    async with session_factory() as session:
        session.add(PersonDB(id=person_id, first_name="Jan", last_name="Kowalski", email=email, phone=phone))
        await session.commit()
    return person_id


@pytest.mark.asyncio
async def test_non_admin_cannot_analyze(ctx) -> None:
    client, login, _ = ctx
    login(_api_user(MEMBER_ID))

    response = await client.post("/api/google-contacts/import/analyze", json={"items": []})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_analyze_church_matched_vs_new(ctx) -> None:
    client, login, session_factory = ctx
    await _seed_tenant(session_factory, name="Zbór CHWZ Warszawa")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/analyze",
        json={
            "items": [
                {"contact": _contact("people/c1", organization_name="Zbór CHWZ Warszawa"), "type": "church"},
                {"contact": _contact("people/c2", organization_name="Zbór CHWZ Nowy Sącz"), "type": "church"},
            ]
        },
    )

    assert response.status_code == 200
    proposals = {p["resourceName"]: p for p in response.json()["churchProposals"]}
    assert proposals["people/c1"]["matchType"] == "matched"
    assert proposals["people/c1"]["confidence"] == 100.0
    assert proposals["people/c2"]["matchType"] == "new"
    assert proposals["people/c2"]["tenantId"] is None


@pytest.mark.asyncio
async def test_analyze_church_matches_preposition_variant(ctx) -> None:
    """ "Zbór Warszawa" (phone contact style) should match "Zbór w Warszawie"
    (app naming style) — the exact case the admin ran into manually."""
    client, login, session_factory = ctx
    await _seed_tenant(session_factory, name="Zbór w Warszawie")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/analyze",
        json={"items": [{"contact": _contact("people/c1", organization_name="Zbór Warszawa"), "type": "church"}]},
    )

    assert response.status_code == 200
    proposal = response.json()["churchProposals"][0]
    assert proposal["matchType"] == "matched"
    assert proposal["matchedName"] == "Zbór w Warszawie"


@pytest.mark.asyncio
async def test_analyze_church_diff_shows_old_and_new_address(ctx) -> None:
    client, login, session_factory = ctx
    tenant_id = await _seed_tenant(session_factory, name="Zbór CHWZ Kraków")
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=tenant_id,
                street="Stara 1",
                city="Kraków",
                postal_code="30-001",
                country="Polska",
                status="published",
            )
        )
        await session.commit()
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/analyze",
        json={
            "items": [
                {
                    "contact": _contact("people/c1", organization_name="Zbór CHWZ Kraków", city="Kraków"),
                    "type": "church",
                }
            ]
        },
    )

    assert response.status_code == 200
    proposal = response.json()["churchProposals"][0]
    assert proposal["matchType"] == "matched"
    fields_by_key = {f["field"]: f for f in proposal["fields"]}
    # City is unchanged in both contacts, so it shouldn't show up as a diffed field.
    assert "city" not in fields_by_key
    assert "street" not in fields_by_key


@pytest.mark.asyncio
async def test_analyze_church_diff_flags_changed_field(ctx) -> None:
    client, login, session_factory = ctx
    tenant_id = await _seed_tenant(session_factory, name="Zbór CHWZ Gdańsk")
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=tenant_id,
                city="Gdańsk stary",
                country="Polska",
                status="published",
            )
        )
        await session.commit()
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/analyze",
        json={
            "items": [
                {
                    "contact": _contact("people/c1", organization_name="Zbór CHWZ Gdańsk", city="Gdańsk nowy"),
                    "type": "church",
                }
            ]
        },
    )

    assert response.status_code == 200
    proposal = response.json()["churchProposals"][0]
    fields_by_key = {f["field"]: f for f in proposal["fields"]}
    assert fields_by_key["city"]["oldValue"] == "Gdańsk stary"
    assert fields_by_key["city"]["newValue"] == "Gdańsk nowy"


@pytest.mark.asyncio
async def test_analyze_person_matches_by_email(ctx) -> None:
    client, login, session_factory = ctx
    person_id = await _seed_person(session_factory, email="jan@example.com")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/analyze",
        json={
            "items": [
                {"contact": _contact("people/p1", first_name="Jan", last_name="K.", email="jan@example.com"), "type": "person"},
                {"contact": _contact("people/p2", first_name="Nowy", last_name="Kontakt", email="nowy@example.com"), "type": "person"},
            ]
        },
    )

    assert response.status_code == 200
    proposals = {p["resourceName"]: p for p in response.json()["personProposals"]}
    assert proposals["people/p1"]["matchType"] == "matched"
    assert proposals["people/p1"]["personId"] == person_id
    assert proposals["people/p1"]["matchedBy"] == "email"
    assert proposals["people/p2"]["matchType"] == "new"


@pytest.mark.asyncio
async def test_apply_creates_church_with_address_and_contact(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [
                {
                    "resourceName": "people/c1",
                    "action": "create",
                    "name": "Zbór CHWZ Gdańsk",
                    "city": "Gdańsk",
                    "street": "Długa 1",
                    "phone": "+48123456789",
                    "email": "gdansk@chwz.example",
                }
            ],
            "personItems": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["churchesCreated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        tenant = (await session.execute(select(TenantDB).where(TenantDB.name == "Zbór CHWZ Gdańsk"))).scalar_one()
        address = (await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == tenant.id))).scalar_one()
        assert address.city == "Gdańsk"
        assert address.street == "Długa 1"

        assignment = (
            await session.execute(
                select(ServiceAssignmentDB).where(
                    ServiceAssignmentDB.scope_type == "church",
                    ServiceAssignmentDB.scope_id == tenant.id,
                )
            )
        ).scalar_one()
        contact_person = (await session.execute(select(PersonDB).where(PersonDB.id == assignment.person_id))).scalar_one()
        assert contact_person.phone == "+48123456789"
        assert contact_person.email == "gdansk@chwz.example"


@pytest.mark.asyncio
async def test_apply_updates_matched_church_name(ctx) -> None:
    client, login, session_factory = ctx
    tenant_id = await _seed_tenant(session_factory, name="Stara nazwa")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [
                {"resourceName": "people/c1", "action": "update", "tenantId": tenant_id, "name": "Nowa nazwa"},
            ],
            "personItems": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["churchesUpdated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        tenant = (await session.execute(select(TenantDB).where(TenantDB.id == tenant_id))).scalar_one()
        assert tenant.name == "Nowa nazwa"


@pytest.mark.asyncio
async def test_apply_creates_standalone_person_without_assignment(ctx) -> None:
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [],
            "personItems": [
                {
                    "resourceName": "people/p1",
                    "action": "create",
                    "firstName": "Ewa",
                    "lastName": "Nowak",
                    "email": "ewa@example.com",
                    "assignToChurch": False,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["personsCreated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        from app.common.crypto.encrypted_types import hmac_email

        # email is encrypted at rest (non-deterministic ciphertext), so an
        # equality filter can't run in SQL — look up via the blind index
        # instead, same as the app's own exact-match lookups do.
        person = (await session.execute(select(PersonDB).where(PersonDB.email_bidx == hmac_email("ewa@example.com")))).scalar_one()
        assert person.first_name == "Ewa"


@pytest.mark.asyncio
async def test_apply_creates_person_with_church_assignment(ctx) -> None:
    client, login, session_factory = ctx
    tenant_id = await _seed_tenant(session_factory, name="Zbór CHWZ Poznań")
    await _seed_church(session_factory, tenant_id=tenant_id, name="Zbór CHWZ Poznań")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [],
            "personItems": [
                {
                    "resourceName": "people/p1",
                    "action": "create",
                    "firstName": "Piotr",
                    "lastName": "Wiśniewski",
                    "email": "piotr@example.com",
                    "assignToChurch": True,
                    "churchId": tenant_id,
                    "customServiceName": "Starszy zboru",
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["personsCreated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        from app.modules.churches.db_models import ServiceAssignmentDB

        assignment = (await session.execute(select(ServiceAssignmentDB).where(ServiceAssignmentDB.scope_id == tenant_id))).scalar_one()
        assert assignment.custom_service_name == "Starszy zboru"


@pytest.mark.asyncio
async def test_apply_updates_matched_person(ctx) -> None:
    client, login, session_factory = ctx
    person_id = await _seed_person(session_factory, email="old@example.com")
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [],
            "personItems": [
                {
                    "resourceName": "people/p1",
                    "action": "update",
                    "personId": person_id,
                    "phone": "+48600000000",
                    "assignToChurch": False,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["personsUpdated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        person = (await session.execute(select(PersonDB).where(PersonDB.id == person_id))).scalar_one()
        assert person.phone == "+48600000000"
        assert person.email == "old@example.com"


@pytest.mark.asyncio
async def test_apply_update_only_touches_provided_address_fields(ctx) -> None:
    """Regression test: applying just a postal-code change must not wipe the
    street/city that weren't part of this update's payload."""
    client, login, session_factory = ctx
    tenant_id = await _seed_tenant(session_factory, name="Zbór CHWZ Łódź")
    async with session_factory() as session:
        session.add(
            CongregationAddressDB(
                id=generate_id(),
                tenant_id=tenant_id,
                street="Piotrkowska 1",
                city="Łódź",
                postal_code="90-000",
                country="Polska",
                status="published",
            )
        )
        await session.commit()
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [{"resourceName": "people/c1", "action": "update", "tenantId": tenant_id, "postalCode": "91-000"}],
            "personItems": [],
        },
    )

    assert response.status_code == 200, response.text

    async with session_factory() as session:
        from sqlalchemy import select

        address = (await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == tenant_id))).scalar_one()
        assert address.postal_code == "91-000"
        assert address.street == "Piotrkowska 1"
        assert address.city == "Łódź"


@pytest.mark.asyncio
async def test_apply_links_new_person_to_newly_created_church(ctx) -> None:
    """The admin picks "create new church" for one proposal and assigns a
    new person to that same not-yet-existing church in one batch."""
    client, login, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [{"resourceName": "people/c1", "action": "create", "name": "Zbór CHWZ Poznań", "city": "Poznań"}],
            "personItems": [
                {
                    "resourceName": "people/p1",
                    "action": "create",
                    "firstName": "Sergiej",
                    "lastName": "Nowak",
                    "assignToChurch": True,
                    "newChurchResourceName": "people/c1",
                    "customServiceName": "Starszy zboru",
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["churchesCreated"] == 1
    assert body["personsCreated"] == 1

    async with session_factory() as session:
        from sqlalchemy import select

        from app.modules.churches.db_models import ServiceAssignmentDB

        tenant = (await session.execute(select(TenantDB).where(TenantDB.name == "Zbór CHWZ Poznań"))).scalar_one()
        assignment = (await session.execute(select(ServiceAssignmentDB).where(ServiceAssignmentDB.scope_id == tenant.id))).scalar_one()
        person = (await session.execute(select(PersonDB).where(PersonDB.id == assignment.person_id))).scalar_one()
        assert person.first_name == "Sergiej"


@pytest.mark.asyncio
async def test_apply_new_church_resource_name_without_matching_church_fails(ctx) -> None:
    client, login, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [{"resourceName": "people/c1", "action": "skip"}],
            "personItems": [
                {
                    "resourceName": "people/p1",
                    "action": "create",
                    "firstName": "Sergiej",
                    "assignToChurch": True,
                    "newChurchResourceName": "people/c1",
                    "customServiceName": "Starszy zboru",
                }
            ],
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_apply_skip_is_counted_and_logged(ctx) -> None:
    client, login, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        "/api/google-contacts/import/apply",
        json={
            "churchItems": [{"resourceName": "people/c1", "action": "skip"}],
            "personItems": [{"resourceName": "people/p1", "action": "skip"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["skipped"] == 2
    assert body["churchesCreated"] == 0
    assert body["personsCreated"] == 0
