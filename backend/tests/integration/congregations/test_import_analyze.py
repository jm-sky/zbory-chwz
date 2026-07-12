"""Tests for POST /admin/congregations/import/analyze.

The AI provider is monkeypatched so these tests never call OpenRouter.
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
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.congregations import import_service as import_service_module
from app.modules.congregations.db_models import CongregationAddressDB, CongregationContactPersonDB
from app.modules.ai.schemas import ExtractedCongregation, ExtractionResult
from app.modules.tenants.db_models import TenantDB
from main import app

ADMIN_ID = "user-admin"
MEMBER_ID = "user-member"
EXISTING_TENANT_ID = "tenant-warszawa"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        isAdmin=is_admin,
        createdAt=datetime.now(UTC),
    )


class _FakeProvider:
    """Stands in for OpenRouterProvider so tests never hit the network."""

    def __init__(self, result: ExtractionResult) -> None:
        self._result = result

    async def extract_congregations(self, raw_text: str) -> ExtractionResult:
        return self._result


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add(
        TenantDB(
            id=EXISTING_TENANT_ID,
            name="ZBÓR W WARSZAWIE",
            status="published",
            owner_id=MEMBER_ID,
            created_at=now,
        )
    )
    session.add(
        CongregationAddressDB(
            id=generate_id(),
            tenant_id=EXISTING_TENANT_ID,
            street="Stara 1",
            city="Warszawa",
            postal_code="00-001",
            country="PL",
            status="published",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        CongregationContactPersonDB(
            id=generate_id(),
            tenant_id=EXISTING_TENANT_ID,
            name="Jan Madeyski",
            title="Diakon",
            phone="+48668292049",
            created_at=now,
        )
    )
    await session.commit()


@pytest_asyncio.fixture
async def ctx(monkeypatch):
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

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        def fake_extraction(result: ExtractionResult) -> None:
            monkeypatch.setattr(
                import_service_module,
                "OpenRouterProvider",
                lambda: _FakeProvider(result),
            )

        yield client, login, fake_extraction, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_analyze_matches_existing_congregation_by_fuzzy_name(ctx) -> None:
    client, login, fake_extraction, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))
    fake_extraction(
        ExtractionResult(
            congregations=[
                ExtractedCongregation(
                    name="Zbor w Warszawie",
                    street="Nowa 5",
                    city="Warszawa",
                    postal_code="00-002",
                    country="PL",
                )
            ]
        )
    )

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["proposals"]) == 1
    proposal = body["proposals"][0]
    assert proposal["match_type"] == "matched"
    assert proposal["tenant_id"] == EXISTING_TENANT_ID
    changed_fields = {f["field"]: f for f in proposal["fields"]}
    assert changed_fields["street"]["old_value"] == "Stara 1"
    assert changed_fields["street"]["new_value"] == "Nowa 5"
    # city/country didn't change, so they shouldn't appear in the diff
    assert "city" not in changed_fields


@pytest.mark.asyncio
async def test_analyze_proposes_new_congregation_when_no_match(ctx) -> None:
    client, login, fake_extraction, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))
    fake_extraction(ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Krakowie", city="Kraków", country="PL")]))

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 200
    proposal = response.json()["proposals"][0]
    assert proposal["match_type"] == "new"
    assert proposal["tenant_id"] is None
    fields = {f["field"]: f["new_value"] for f in proposal["fields"]}
    assert fields["city"] == "Kraków"


@pytest.mark.asyncio
async def test_analyze_ignores_phone_formatting_differences(ctx) -> None:
    client, login, fake_extraction, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))
    fake_extraction(
        ExtractionResult(
            congregations=[
                ExtractedCongregation(
                    name="Zbor w Warszawie",
                    contact_name="Jan Madeyski",
                    contact_title="Diakon",
                    contact_phone="668-292-049",
                )
            ]
        )
    )

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 200
    proposal = response.json()["proposals"][0]
    fields = {f["field"] for f in proposal["fields"]}
    # "668-292-049" and the stored "+48668292049" are the same number once
    # normalized, so no field should be proposed as changed.
    assert "contact_phone" not in fields
    assert proposal["contact_context"] is None


@pytest.mark.asyncio
async def test_analyze_proposes_normalized_phone_when_number_actually_changes(ctx) -> None:
    client, login, fake_extraction, _ = ctx
    login(_api_user(ADMIN_ID, is_admin=True))
    fake_extraction(
        ExtractionResult(
            congregations=[
                ExtractedCongregation(
                    name="Zbor w Warszawie",
                    contact_name="Jan Madeyski",
                    contact_title="Diakon",
                    contact_phone="500-100-200",
                )
            ]
        )
    )

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 200
    proposal = response.json()["proposals"][0]
    fields = {f["field"]: f for f in proposal["fields"]}
    assert fields["contact_phone"]["group"] == "contact"
    assert fields["contact_phone"]["old_value"] == "+48668292049"
    assert fields["contact_phone"]["new_value"] == "+48500100200"
    assert proposal["contact_context"] == "Diakon: Jan Madeyski"


@pytest.mark.asyncio
async def test_analyze_matches_correct_contact_among_several(ctx) -> None:
    """A congregation with two deacons must not treat the first one as "the"
    contact - the extracted name should be matched to the right person."""
    client, login, fake_extraction, session_factory = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    async with session_factory() as session:
        session.add(
            CongregationContactPersonDB(
                id=generate_id(),
                tenant_id=EXISTING_TENANT_ID,
                name="Marek Kowalski",
                title="Diakon",
                phone="+48111222333",
                order=0,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()

    fake_extraction(
        ExtractionResult(
            congregations=[
                ExtractedCongregation(
                    name="Zbor w Warszawie",
                    contact_name="Jan Madeyski",
                    contact_title="Diakon",
                    contact_phone="668-292-049",
                )
            ]
        )
    )

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 200
    proposal = response.json()["proposals"][0]

    async with session_factory() as session:
        result = await session.execute(select(CongregationContactPersonDB).where(CongregationContactPersonDB.name == "Jan Madeyski"))
        jan = result.scalar_one()

    # Jan Madeyski already exists with the exact same data, so this is a
    # 100% match and no fields should be proposed as changed - and it must
    # never be confused with the other deacon, Marek Kowalski.
    fields = {f["field"] for f in proposal["fields"]}
    assert "contact_name" not in fields
    assert "contact_phone" not in fields
    assert proposal["contact_person_id"] == jan.id


@pytest.mark.asyncio
async def test_analyze_requires_admin(ctx) -> None:
    client, login, fake_extraction, _ = ctx
    login(_api_user(MEMBER_ID))
    fake_extraction(ExtractionResult(congregations=[]))

    response = await client.post("/api/admin/congregations/import/analyze", json={"raw_text": "notatka"})

    assert response.status_code == 403
