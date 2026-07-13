"""Tests for SenderResolver — clergy e-mail sender identification/authorization.

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.auth.db_models import UserDB
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, RegionDB, ServiceAssignmentDB
from app.modules.congregations.sender_resolver import SenderResolver
from app.modules.tenants.db_models import TenantDB


async def _make_tenant_and_church(
    session: AsyncSession,
    owner_id: str,
    *,
    name: str,
    community_id: str,
    region_id: str | None = None,
) -> TenantDB:
    tenant = TenantDB(id=generate_id(), name=name, status="published", owner_id=owner_id)
    session.add(tenant)
    await session.flush()
    session.add(
        ChurchDB(
            id=tenant.id,  # ChurchDB.id == tenant.id by construction, see churches/provisioning.py
            community_id=community_id,
            region_id=region_id,
            tenant_id=owner_id,  # unrelated org-level tenant_id column; irrelevant here
            name=name,
        )
    )
    return tenant


@pytest_asyncio.fixture
async def setup() -> AsyncGenerator[dict, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        owner = UserDB(id=generate_id(), email="owner@example.com", name="Owner", hashed_password="x")
        session.add(owner)
        await session.flush()

        community = CommunityDB(id=generate_id(), name="CHWZ", slug="chwz", visibility="hidden")
        session.add(community)
        await session.flush()

        region = RegionDB(id=generate_id(), community_id=community.id, name="Region Zachodni", slug="zachodni")
        session.add(region)
        await session.flush()

        home_church = await _make_tenant_and_church(session, owner.id, name="Zbór w Świebodzinie", community_id=community.id, region_id=region.id)
        other_in_region = await _make_tenant_and_church(session, owner.id, name="Zbór w Zielonej Górze", community_id=community.id, region_id=region.id)
        other_community = await _make_tenant_and_church(session, owner.id, name="Zbór w Warszawie", community_id=community.id, region_id=None)
        await session.flush()

        pastor = PersonDB(id=generate_id(), first_name="Jan", last_name="Kowalski", email="pastor@example.com")
        session.add(pastor)
        await session.flush()
        session.add(ServiceAssignmentDB(id=generate_id(), person_id=pastor.id, scope_type="church", scope_id=home_church.id))

        regional_bishop = PersonDB(id=generate_id(), first_name="Adam", last_name="Nowak", email="bishop@example.com")
        session.add(regional_bishop)
        await session.flush()
        session.add(ServiceAssignmentDB(id=generate_id(), person_id=regional_bishop.id, scope_type="region", scope_id=region.id))

        no_home_bishop = PersonDB(id=generate_id(), first_name="Piotr", last_name="Wiśniewski", email="national@example.com")
        session.add(no_home_bishop)
        await session.flush()
        session.add(ServiceAssignmentDB(id=generate_id(), person_id=no_home_bishop.id, scope_type="community", scope_id=community.id))

        await session.commit()

        tenants = list((await session.execute(select(TenantDB))).scalars().all())
        name_slugs = {t.id: t.name.lower().replace(" ", "-") for t in tenants}

        yield {
            "resolver": SenderResolver(session),
            "tenants": tenants,
            "name_slugs": name_slugs,
            "home_church": home_church,
            "other_in_region": other_in_region,
            "other_community": other_community,
        }

    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_sender(setup: dict) -> None:
    result = await setup["resolver"].resolve("stranger@example.com", None, setup["tenants"], setup["name_slugs"])
    assert result.kind == "unknown_sender"
    assert result.person is None
    assert result.tenant_id is None


@pytest.mark.asyncio
async def test_pastor_no_location_defaults_to_own_church(setup: dict) -> None:
    result = await setup["resolver"].resolve("pastor@example.com", None, setup["tenants"], setup["name_slugs"])
    assert result.kind == "own_church"
    assert result.tenant_id == setup["home_church"].id


@pytest.mark.asyncio
async def test_regional_bishop_no_location_is_ambiguous(setup: dict) -> None:
    # No church-scope assignment of their own (only region-scope) -> no default target.
    result = await setup["resolver"].resolve("bishop@example.com", None, setup["tenants"], setup["name_slugs"])
    assert result.kind == "ambiguous"
    assert result.tenant_id is None


@pytest.mark.asyncio
async def test_regional_bishop_matches_own_region(setup: dict) -> None:
    result = await setup["resolver"].resolve("bishop@example.com", "Zbór w Zielonej Górze", setup["tenants"], setup["name_slugs"])
    assert result.kind == "matched_by_name"
    assert result.tenant_id == setup["other_in_region"].id


@pytest.mark.asyncio
async def test_regional_bishop_unauthorized_outside_region(setup: dict) -> None:
    result = await setup["resolver"].resolve("bishop@example.com", "Zbór w Warszawie", setup["tenants"], setup["name_slugs"])
    assert result.kind == "unauthorized"
    assert result.tenant_id == setup["other_community"].id


@pytest.mark.asyncio
async def test_national_bishop_authorized_via_community(setup: dict) -> None:
    result = await setup["resolver"].resolve("national@example.com", "Zbór w Warszawie", setup["tenants"], setup["name_slugs"])
    assert result.kind == "matched_by_name"
    assert result.tenant_id == setup["other_community"].id


@pytest.mark.asyncio
async def test_no_name_match_is_ambiguous(setup: dict) -> None:
    result = await setup["resolver"].resolve("pastor@example.com", "Zupełnie inna nazwa spoza bazy", setup["tenants"], setup["name_slugs"])
    assert result.kind == "ambiguous"


@pytest.mark.asyncio
async def test_sender_email_matched_case_insensitively(setup: dict) -> None:
    result = await setup["resolver"].resolve("PASTOR@EXAMPLE.COM", None, setup["tenants"], setup["name_slugs"])
    assert result.kind == "own_church"
