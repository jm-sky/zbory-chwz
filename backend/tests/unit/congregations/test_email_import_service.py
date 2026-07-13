"""Tests for EmailImportService.poll_and_process (fetch -> resolve -> extract ->
verify -> auto-apply-or-queue). IMAP and the AI provider are faked.

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.id_utils import generate_id
from app.core.database import Base
from app.modules.ai.schemas import ExtractedCongregation, ExtractionResult, VerificationResult
from app.modules.auth.db_models import UserDB
from app.modules.churches.db_models import ChurchDB, CommunityDB, PersonDB, ServiceAssignmentDB
from app.modules.congregations import email_import_service as svc_module
from app.modules.congregations.db_models import CongregationAddressDB
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB, EmailImportMessageDB
from app.modules.congregations.imap_client import InboundEmail
from app.modules.tenants.db_models import TenantDB


class _FakeImapClient:
    """Stands in for ImapClient: no real socket, canned messages, records mark_seen calls."""

    instances: list["_FakeImapClient"] = []

    def __init__(self, settings: object) -> None:
        self.emails: list[InboundEmail] = []
        self.seen: list[str] = []
        _FakeImapClient.instances.append(self)

    def __enter__(self) -> "_FakeImapClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def fetch_unseen(self) -> list[InboundEmail]:
        return self.emails

    def mark_seen(self, uid: str) -> None:
        self.seen.append(uid)


def _inbound(
    from_address: str,
    text_body: str,
    message_id: str | None = None,
    uid: str = "1",
    *,
    auth_spf: str | None = "pass",
    auth_dkim: str | None = "pass",
    auth_dmarc: str | None = "pass",
) -> InboundEmail:
    return InboundEmail(
        imap_uid=uid,
        message_id=message_id,
        from_address=from_address,
        subject="Aktualizacja danych",
        text_body=text_body,
        auth_spf=auth_spf,
        auth_dkim=auth_dkim,
        auth_dmarc=auth_dmarc,
    )


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[object, None]:
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

        tenant = TenantDB(id=generate_id(), name="Zbór w Świebodzinie", status="published", owner_id=owner.id)
        session.add(tenant)
        await session.flush()
        session.add(ChurchDB(id=tenant.id, community_id=community.id, region_id=None, tenant_id=owner.id, name=tenant.name))
        session.add(CongregationAddressDB(id=generate_id(), tenant_id=tenant.id, church_id=tenant.id, city="Świebodzin", country="PL", status="published"))

        pastor = PersonDB(id=generate_id(), first_name="Jan", last_name="Kowalski", email="pastor@example.com")
        session.add(pastor)
        await session.flush()
        session.add(ServiceAssignmentDB(id=generate_id(), person_id=pastor.id, scope_type="church", scope_id=tenant.id))

        other_person = PersonDB(id=generate_id(), first_name="Anna", last_name="Nowak", email="anna@example.com")
        session.add(other_person)

        await session.commit()
        session.tenant_id = tenant.id  # type: ignore[attr-defined]
        session.pastor_id = pastor.id  # type: ignore[attr-defined]

        yield session

    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_fake_imap() -> None:
    _FakeImapClient.instances = []


def _fake_settings(*, enabled: bool = True, trust_threshold: float = 0.9, superadmin_email: str | None = "admin@example.com") -> SimpleNamespace:
    return SimpleNamespace(
        email_import=SimpleNamespace(enabled=enabled, trust_auto_apply_threshold=trust_threshold),
        security=SimpleNamespace(superadmin_email=superadmin_email),
    )


def _patch_imap(monkeypatch: pytest.MonkeyPatch, emails: list[InboundEmail], **settings_kwargs: object) -> _FakeImapClient:
    client = _FakeImapClient(settings=None)
    client.emails = emails
    monkeypatch.setattr(svc_module, "ImapClient", lambda settings: client)
    monkeypatch.setattr(svc_module, "get_settings", lambda: _fake_settings(**settings_kwargs))  # type: ignore[arg-type]
    return client


def _patch_ai(
    monkeypatch: pytest.MonkeyPatch,
    result: ExtractionResult,
    *,
    trust_score: float = 0.95,
    reasoning: str = "Spójne z rozpoznanym nadawcą.",
) -> MagicMock:
    fake_provider = MagicMock()
    fake_provider.last_context_hint = "UNCALLED"
    fake_provider.extract_call_count = 0
    fake_provider.verify_call_count = 0
    fake_provider.last_diff_summary = None

    async def _extract(raw_text: str, *, context_hint: str | None = None) -> ExtractionResult:
        fake_provider.last_context_hint = context_hint
        fake_provider.extract_call_count += 1
        return result

    async def _verify(raw_text: str, sender_context: str, diff_summary: str) -> VerificationResult:
        fake_provider.verify_call_count += 1
        fake_provider.last_diff_summary = diff_summary
        return VerificationResult(trust_score=trust_score, reasoning=reasoning)

    fake_provider.extract_congregations = _extract
    fake_provider.verify_extraction = _verify
    monkeypatch.setattr(svc_module, "OpenRouterProvider", lambda: fake_provider)
    return fake_provider


def _patch_email_service(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake_service = MagicMock()
    fake_service.send_email = AsyncMock(return_value=True)
    monkeypatch.setattr(svc_module, "get_email_service", lambda: fake_service)
    return fake_service


@pytest.mark.asyncio
async def test_disabled_skips_poll(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc_module, "get_settings", lambda: _fake_settings(enabled=False))
    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    result = await service.poll_and_process()
    assert result.fetched == 0
    assert result.processed == 0


@pytest.mark.asyncio
async def test_unknown_sender_is_queued_without_ai_call(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("stranger@example.com", "Zmieńcie mój numer telefonu.")
    _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    provider = _patch_ai(monkeypatch, ExtractionResult(congregations=[]))

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    result = await service.poll_and_process()

    assert result.processed == 1
    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert len(rows) == 1
    assert rows[0].resolution == "unknown_sender"
    assert rows[0].resolved_tenant_id is None
    assert provider.extract_call_count == 0  # AI extraction is never called for unknown senders


@pytest.mark.asyncio
async def test_high_trust_change_is_auto_applied_and_logged(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Nasz nowy numer telefonu to 600 111 222.", message_id="<abc@example.com>")
    _patch_imap(monkeypatch, [email], trust_threshold=0.9)
    email_service = _patch_email_service(monkeypatch)
    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie", contact_phone="600111222")])
    provider = _patch_ai(monkeypatch, extraction, trust_score=0.95)

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    result = await service.poll_and_process()

    assert result.processed == 1
    assert provider.last_context_hint is not None and "Świebodzinie" in provider.last_context_hint
    assert provider.verify_call_count == 1

    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert rows[0].resolution == "matched_by_name"
    assert rows[0].resolved_tenant_id == db.tenant_id  # type: ignore[attr-defined]
    assert rows[0].status == "auto_applied"
    assert rows[0].verification_score == 0.95

    log_rows = list((await db.execute(select(CongregationChangeLogDB))).scalars().all())  # type: ignore[attr-defined]
    assert len(log_rows) == 1
    assert log_rows[0].field == "contact_phone"
    assert log_rows[0].new_value == "+48600111222"
    assert log_rows[0].source == "email_auto"
    assert log_rows[0].actor_person_id == db.pastor_id  # type: ignore[attr-defined]
    assert log_rows[0].email_import_message_id == rows[0].id

    email_service.send_email.assert_awaited_once()
    assert email_service.send_email.call_args.kwargs["to"] == "admin@example.com"


@pytest.mark.asyncio
async def test_low_trust_change_is_queued_not_applied(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Nasz nowy numer telefonu to 600 111 222.")
    _patch_imap(monkeypatch, [email], trust_threshold=0.9)
    email_service = _patch_email_service(monkeypatch)
    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie", contact_phone="600111222")])
    _patch_ai(monkeypatch, extraction, trust_score=0.4, reasoning="Treść nie uzasadnia zmiany.")

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    await service.poll_and_process()

    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert rows[0].status == "pending"
    assert rows[0].verification_score == 0.4
    assert rows[0].verification_reasoning == "Treść nie uzasadnia zmiany."

    log_rows = list((await db.execute(select(CongregationChangeLogDB))).scalars().all())  # type: ignore[attr-defined]
    assert log_rows == []
    email_service.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_spf_fail_skips_ai_verification_and_stays_pending(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Nasz nowy numer telefonu to 600 111 222.", auth_spf="fail")
    _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie", contact_phone="600111222")])
    provider = _patch_ai(monkeypatch, extraction, trust_score=0.99)

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    await service.poll_and_process()

    assert provider.verify_call_count == 0  # never spend an AI call once the auth gate already fails
    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert rows[0].status == "pending"
    assert rows[0].verification_score is None


@pytest.mark.asyncio
async def test_no_changed_fields_is_queued_without_verification(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Tylko pozdrowienia, bez zmian.")
    _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie")])
    provider = _patch_ai(monkeypatch, extraction, trust_score=0.99)

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    await service.poll_and_process()

    assert provider.verify_call_count == 0
    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert rows[0].status == "pending"
    assert rows[0].resolution == "matched_by_name"


@pytest.mark.asyncio
async def test_multiple_extracted_congregations_is_ambiguous(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Dwa zbory naraz się zmieniły.")
    _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    extraction = ExtractionResult(
        congregations=[
            ExtractedCongregation(name="Zbór w Świebodzinie"),
            ExtractedCongregation(name="Zbór w Zielonej Górze"),
        ]
    )
    _patch_ai(monkeypatch, extraction)

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    await service.poll_and_process()

    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert rows[0].resolution == "ambiguous"
    assert rows[0].resolved_tenant_id is None


@pytest.mark.asyncio
async def test_duplicate_message_id_is_skipped(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Coś tam", message_id="<dup@example.com>")
    client = _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    extraction = ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie")])
    _patch_ai(monkeypatch, extraction)

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    first = await service.poll_and_process()
    assert first.processed == 1

    client.emails = [email]  # simulate the same message still being UNSEEN somehow
    second = await service.poll_and_process()
    assert second.skipped_duplicate == 1
    assert second.processed == 0

    rows = list((await db.execute(select(EmailImportMessageDB))).scalars().all())  # type: ignore[attr-defined]
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_marks_seen_only_after_successful_processing(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    email = _inbound("pastor@example.com", "Coś tam", uid="42")
    client = _patch_imap(monkeypatch, [email])
    _patch_email_service(monkeypatch)
    _patch_ai(monkeypatch, ExtractionResult(congregations=[ExtractedCongregation(name="Zbór w Świebodzinie")]))

    service = svc_module.EmailImportService(db)  # type: ignore[arg-type]
    await service.poll_and_process()

    assert client.seen == ["42"]
