"""Tests for the clergy e-mail import review queue endpoints
(GET/POST /admin/congregations/import/inbox...).

See docs/plans/2026-07-13--clergy-email-updates.md.
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
from app.modules.ai.schemas import ExtractedCongregation, ExtractionResult
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, ServiceAssignmentDB
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB, EmailImportMessageDB
from app.modules.tenants.db_models import TenantDB
from main import app

ADMIN_ID = "user-admin"
TENANT_ID = "tenant-swiebodzin"
PERSON_ID = "person-pastor"


def _api_user(user_id: str, *, is_admin: bool = False) -> User:
    return User(id=user_id, email=f"{user_id}@example.com", name=user_id, isAdmin=is_admin, createdAt=datetime.now(UTC))


async def _seed(session: AsyncSession) -> str:
    now = datetime.now(UTC)
    session.add(TenantDB(id=TENANT_ID, name="Zbór w Świebodzinie", status="published", owner_id=ADMIN_ID, created_at=now))
    community = CommunityDB(id=generate_id(), name="CHWZ", slug="chwz", visibility="hidden")
    session.add(community)
    await session.flush()
    session.add(ChurchDB(id=TENANT_ID, community_id=community.id, region_id=None, tenant_id=ADMIN_ID, name="Zbór w Świebodzinie"))
    session.add(CongregationAddressDB(id=generate_id(), tenant_id=TENANT_ID, church_id=TENANT_ID, city="Świebodzin", country="PL", status="published"))
    session.add(PersonDB(id=PERSON_ID, first_name="Jan", last_name="Kowalski", email="pastor@example.com"))
    await session.flush()
    session.add(ServiceAssignmentDB(id=generate_id(), person_id=PERSON_ID, scope_type="church", scope_id=TENANT_ID))

    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie", contact_phone="600111222")])
    message_id = generate_id()
    session.add(
        EmailImportMessageDB(
            id=message_id,
            message_id="<msg-1@example.com>",
            raw_from="pastor@example.com",
            sender_person_id=PERSON_ID,
            resolved_tenant_id=TENANT_ID,
            resolution="matched_by_name",
            auth_spf="pass",
            auth_dkim="pass",
            auth_dmarc="pass",
            extraction_json=extraction.model_dump_json(),
            verification_score=0.6,
            verification_reasoning="Poniżej progu auto-apply.",
            status="pending",
        )
    )
    await session.commit()
    return message_id


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
        message_id = await _seed(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def login(user: User) -> None:
            app.dependency_overrides[get_current_user] = lambda: user

        yield client, login, session_factory, message_id

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_inbox_includes_proposal_diff(ctx) -> None:
    client, login, _, message_id = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.get("/api/admin/congregations/import/inbox")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["message_id"] == message_id
    assert item["sender_label"] == "Jan Kowalski"
    assert item["resolution"] == "matched_by_name"
    assert item["verification_score"] == 0.6
    assert item["proposal"] is not None
    fields = {f["field"]: f for f in item["proposal"]["fields"]}
    assert fields["contact_phone"]["new_value"] == "+48600111222"
    assert fields["contact_phone"]["old_value"] is None


@pytest.mark.asyncio
async def test_approve_applies_fields_and_logs_change(ctx) -> None:
    client, login, session_factory, message_id = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(
        f"/api/admin/congregations/import/inbox/{message_id}/approve",
        json={"fields": [{"field": "contact_phone", "value": "+48600111222", "apply": True}]},
    )

    assert response.status_code == 200
    assert response.json() == {"created": 0, "updated": 1, "skipped": 0}

    async with session_factory() as session:
        message = (await session.execute(select(EmailImportMessageDB).where(EmailImportMessageDB.id == message_id))).scalar_one()
        assert message.status == "approved"
        assert message.reviewed_by_user_id == ADMIN_ID

        log = (await session.execute(select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == TENANT_ID))).scalars().all()
        assert len(log) == 1
        assert log[0].field == "contact_phone"
        assert log[0].source == "email_reviewed"
        assert log[0].actor_user_id == ADMIN_ID
        assert log[0].email_import_message_id == message_id

        address = (await session.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == TENANT_ID))).scalar_one()
        assert address.last_updated_label is not None


@pytest.mark.asyncio
async def test_approve_twice_conflicts(ctx) -> None:
    client, login, _, message_id = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    first = await client.post(
        f"/api/admin/congregations/import/inbox/{message_id}/approve",
        json={"fields": [{"field": "contact_phone", "value": "+48600111222", "apply": True}]},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/admin/congregations/import/inbox/{message_id}/approve",
        json={"fields": [{"field": "contact_phone", "value": "+48600111222", "apply": True}]},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_reject_marks_message_rejected(ctx) -> None:
    client, login, session_factory, message_id = ctx
    login(_api_user(ADMIN_ID, is_admin=True))

    response = await client.post(f"/api/admin/congregations/import/inbox/{message_id}/reject")

    assert response.status_code == 204
    async with session_factory() as session:
        message = (await session.execute(select(EmailImportMessageDB).where(EmailImportMessageDB.id == message_id))).scalar_one()
        assert message.status == "rejected"
        assert message.reviewed_by_user_id == ADMIN_ID


@pytest.mark.asyncio
async def test_non_admin_cannot_access_inbox(ctx) -> None:
    client, login, _, _ = ctx
    login(_api_user("user-plain", is_admin=False))

    response = await client.get("/api/admin/congregations/import/inbox")

    assert response.status_code == 403
