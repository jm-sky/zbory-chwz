"""G8 — every ACL-affecting write path leaves exactly one (or one-per-grant) audit row
with the right actor, target, and scope: role grant (service assignment + createAccount),
role revoke (cascading on assignment delete), and invite sent."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.auth.db_models import UserDB
from app.modules.auth.models import User
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, ServiceAssignmentDB, ServiceTypeDB
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import ServiceAssignmentCreateRequest
from app.modules.governance.db_models import AclAuditAction, AclAuditLogDB


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db

    await engine.dispose()


def _admin() -> User:
    return User(id="admin", email="admin@example.com", name="Admin", isAdmin=True, createdAt=datetime.now(UTC))


async def _seed_church(session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    community_id = generate_id()
    church_id = generate_id()
    service_type_id = generate_id()

    session.add_all(
        [
            CommunityDB(id=community_id, name="CHWZ", slug="chwz", created_at=now),
            ChurchDB(
                id=church_id,
                community_id=community_id,
                region_id=None,
                tenant_id=church_id,
                name="Zbor",
                visibility="hidden",
                created_at=now,
            ),
            ServiceTypeDB(
                id=service_type_id,
                slug="diacon-test",
                name="Diakon",
                scope_type="church",
                suggested_role="diacon",
                sort_order=0,
                created_at=now,
            ),
        ]
    )
    await session.flush()
    return {"church_id": church_id, "service_type_id": service_type_id}


@pytest.mark.asyncio
async def test_role_grant_leaves_one_audit_row(session: AsyncSession) -> None:
    world = await _seed_church(session)
    admin = _admin()
    repo = ChurchRepository(session)

    payload = ServiceAssignmentCreateRequest(
        firstName="Jan",
        lastName="Kowalski",
        email="jan@example.com",
        serviceTypeId=world["service_type_id"],
        createAccount=True,
        suggestedRole="diacon",
    )
    permission_service = PermissionService(session, PermissionCache(None))
    await repo.create_service_assignment("church", world["church_id"], payload, actor=admin, permission_service=permission_service)

    rows = (await session.execute(select(AclAuditLogDB))).scalars().all()
    grant_rows = [r for r in rows if r.action == AclAuditAction.ROLE_GRANT.value]
    assert len(grant_rows) == 1
    row = grant_rows[0]
    assert row.actor_user_id == "admin"
    assert row.actor_label == "Admin"
    assert row.target_label == "Jan Kowalski"
    assert row.role_name == "diacon"
    assert row.scope_type == "church"
    assert row.scope_id == world["church_id"]


@pytest.mark.asyncio
async def test_role_revoke_on_assignment_delete_leaves_one_row_per_grant(session: AsyncSession) -> None:
    world = await _seed_church(session)
    admin = _admin()
    repo = ChurchRepository(session)

    payload = ServiceAssignmentCreateRequest(
        firstName="Jan",
        lastName="Kowalski",
        email="jan@example.com",
        serviceTypeId=world["service_type_id"],
        createAccount=True,
        suggestedRole="diacon",
    )
    permission_service = PermissionService(session, PermissionCache(None))
    assignment = await repo.create_service_assignment("church", world["church_id"], payload, actor=admin, permission_service=permission_service)

    result = await repo.delete_service_assignment("church", world["church_id"], assignment.id, actor=admin)
    assert result.deleted
    assert len(result.revoked_roles) == 1

    rows = (await session.execute(select(AclAuditLogDB))).scalars().all()
    revoke_rows = [r for r in rows if r.action == AclAuditAction.ROLE_REVOKE.value]
    assert len(revoke_rows) == 1
    row = revoke_rows[0]
    assert row.actor_user_id == "admin"
    assert row.role_name == "diacon"
    assert row.scope_type == "church"
    assert row.scope_id == world["church_id"]


@pytest.mark.asyncio
async def test_invite_sent_leaves_one_audit_row(session: AsyncSession) -> None:
    world = await _seed_church(session)
    admin = _admin()
    repo = ChurchRepository(session)

    now = datetime.now(UTC)
    invitee = UserDB(id=generate_id(), email="invitee@example.com", name="Invitee", is_active=False)
    session.add(invitee)
    person = PersonDB(id=generate_id(), first_name="Invitee", last_name="Person", email="invitee@example.com", user_id=invitee.id)
    session.add(person)
    await session.flush()
    assignment = ServiceAssignmentDB(
        id=generate_id(),
        person_id=person.id,
        service_type_id=world["service_type_id"],
        scope_type="church",
        scope_id=world["church_id"],
        created_at=now,
    )
    session.add(assignment)
    await session.commit()

    assignment.person = person
    await repo.invite_assignment_account(assignment, actor=admin)

    rows = (await session.execute(select(AclAuditLogDB))).scalars().all()
    invite_rows = [r for r in rows if r.action == AclAuditAction.INVITE_SENT.value]
    assert len(invite_rows) == 1
    row = invite_rows[0]
    assert row.actor_user_id == "admin"
    assert row.target_user_id == invitee.id
    assert row.target_label == "Invitee"
    assert row.scope_type == "church"
    assert row.scope_id == world["church_id"]
