"""Tests for ChurchRepository.search_persons.

Covers the 2026-07-11 decision (docs/plans/2026-07-09--people-groups.md) to
extend the person search used by the group/service-assignment autocomplete:
match on phone too, and match "First Last" against the separate
first_name/last_name columns regardless of word order.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.churches.db_models import PersonDB
from app.modules.churches.repositories import ChurchRepository


@pytest_asyncio.fixture
async def repo() -> AsyncGenerator[ChurchRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add_all(
            [
                PersonDB(
                    id=generate_id(),
                    first_name="Jan",
                    last_name="Kowalski",
                    email="jan.kowalski@example.com",
                    phone="+48 600 000 000",
                ),
                PersonDB(
                    id=generate_id(),
                    first_name="Anna",
                    last_name="Nowak",
                    email="anna.nowak@example.com",
                    phone="+48 700 000 000",
                ),
            ]
        )
        await session.commit()

        yield ChurchRepository(session)

    await engine.dispose()


@pytest.mark.asyncio
async def test_search_matches_phone(repo: ChurchRepository) -> None:
    results = await repo.search_persons("+48 600 000 000")
    assert [p.first_name for p in results] == ["Jan"]


@pytest.mark.asyncio
async def test_search_matches_phone_ignoring_formatting(
    repo: ChurchRepository,
) -> None:
    """Stored as "+48 600 000 000" — typing it without spaces must still match."""
    results = await repo.search_persons("600000000")
    assert [p.first_name for p in results] == ["Jan"]


@pytest.mark.asyncio
async def test_search_matches_full_name_in_natural_order(
    repo: ChurchRepository,
) -> None:
    results = await repo.search_persons("Jan Kowalski")
    assert [p.first_name for p in results] == ["Jan"]


@pytest.mark.asyncio
async def test_search_matches_full_name_in_reversed_order(
    repo: ChurchRepository,
) -> None:
    results = await repo.search_persons("Kowalski Jan")
    assert [p.first_name for p in results] == ["Jan"]


@pytest.mark.asyncio
async def test_search_two_words_does_not_cross_match_different_people(
    repo: ChurchRepository,
) -> None:
    results = await repo.search_persons("Jan Nowak")
    assert results == []


@pytest.mark.asyncio
async def test_search_still_matches_single_field(repo: ChurchRepository) -> None:
    results = await repo.search_persons("anna")
    assert [p.first_name for p in results] == ["Anna"]
