"""Orchestrates polling the clergy e-mail update mailbox.

Phase 3+4 (docs/plans/2026-07-13--clergy-email-updates.md): fetch unseen
mail, resolve the sender and target congregation, run the AI extraction
pipeline, and either queue the proposal for admin review or - if every gate
in `_maybe_apply` passes - apply it immediately and log the change.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.common.pii import mask_email
from app.core.config import get_settings
from app.core.email.service import get_email_service
from app.modules.ai.provider import OpenRouterProvider
from app.modules.ai.schemas import ExtractionResult
from app.modules.churches.contact_sync import assignment_title
from app.modules.churches.db_models import PersonDB
from app.modules.churches.repositories import ChurchRepository
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB, EmailImportMessageDB
from app.modules.congregations.field_diff import FIELD_GROUPS, FIELD_LABELS, FieldDiff, build_field_diff, new_value_format_plausible
from app.modules.congregations.imap_client import ImapClient, InboundEmail
from app.modules.congregations.import_service import CongregationImportService
from app.modules.congregations.repositories import CongregationRepository
from app.modules.congregations.sender_resolver import SenderResolution, SenderResolver
from app.modules.congregations.tenant_matching import match_slug
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository

logger = logging.getLogger(__name__)

# Below this rapidfuzz partial_ratio (0-100), the sender's known name is
# treated as absent from the e-mail body — used as a local stand-in for what
# the AI verification prompt used to judge itself from the sender's name
# (now withheld from the prompt, see _resolve_and_maybe_apply).
SIGNATURE_MATCH_THRESHOLD = 80.0


@dataclass
class PollResult:
    fetched: int = 0
    processed: int = 0
    skipped_duplicate: int = 0


def _person_label(person: PersonDB) -> str:
    name = " ".join(part for part in (person.first_name, person.last_name) if part).strip()
    return name or person.email or "Nieznany nadawca"


def _signature_mentions_sender(raw_text: str, sender_name: str) -> bool:
    """Local stand-in for the "does the signature/tone match the recognized
    sender" judgment the AI prompt used to make from the sender's name — now
    computed here instead, so that name never has to leave the server (see
    _resolve_and_maybe_apply)."""
    if not sender_name.strip():
        return False
    return fuzz.partial_ratio(sender_name.lower(), raw_text.lower()) >= SIGNATURE_MATCH_THRESHOLD


class EmailImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._resolver = SenderResolver(db)
        self._tenant_repo = TenantRepository(db)
        self._congregation_repo = CongregationRepository(db)
        self._church_repo = ChurchRepository(db)

    async def poll_and_process(self) -> PollResult:
        settings = get_settings().email_import
        if not settings.enabled:
            logger.info("Email import disabled (EMAIL_IMPORT_ENABLED=false); skipping poll")
            return PollResult()

        with ImapClient(settings) as client:
            emails = await asyncio.to_thread(client.fetch_unseen)

            tenants = await self._tenant_repo.list_all()
            name_slugs = {t.id: match_slug(t.name) for t in tenants}
            tenant_names = {t.id: t.name for t in tenants}

            result = PollResult(fetched=len(emails))
            for inbound in emails:
                if inbound.message_id and await self._already_processed(inbound.message_id):
                    result.skipped_duplicate += 1
                    await asyncio.to_thread(client.mark_seen, inbound.imap_uid)
                    continue

                try:
                    await self._process_one(inbound, tenants, name_slugs, tenant_names)
                    result.processed += 1
                except Exception:
                    logger.exception("Failed processing inbound e-mail from %s; leaving unseen for retry", mask_email(inbound.from_address))
                    continue

                await asyncio.to_thread(client.mark_seen, inbound.imap_uid)

            return result

    async def _already_processed(self, message_id: str) -> bool:
        result = await self.db.execute(select(EmailImportMessageDB.id).where(EmailImportMessageDB.message_id == message_id))
        return result.scalar_one_or_none() is not None

    async def _process_one(
        self,
        inbound: InboundEmail,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
        tenant_names: dict[str, str],
    ) -> None:
        if not inbound.from_address:
            await self._save_message(inbound, resolution="unknown_sender", sender_person_id=None, tenant_id=None, extraction=None)
            return

        # Pre-check without an AI-extracted name: does the sender have a
        # single home church? If so, hint the AI with its name so it can
        # fill the (required) `name` field even when the e-mail itself never
        # states which zbór it's about (see OpenRouterProvider.extract_congregations).
        precheck = await self._resolver.resolve(inbound.from_address, None, tenants, name_slugs)
        if precheck.kind == "unknown_sender":
            await self._save_message(inbound, resolution="unknown_sender", sender_person_id=None, tenant_id=None, extraction=None)
            return

        context_hint = None
        if precheck.kind == "own_church" and precheck.tenant_id:
            church_name = tenant_names.get(precheck.tenant_id, "")
            context_hint = f"Kontekst: nadawca jest osobą kontaktową zboru '{church_name}'. " "Jeśli w treści maila nie podano innej nazwy ani miasta zboru, przyjmij, " "że aktualizacja dotyczy właśnie tego zboru."

        provider = OpenRouterProvider()
        extraction = await provider.extract_congregations(inbound.text_body, context_hint=context_hint)

        if len(extraction.congregations) != 1:
            # Nothing usable extracted, or more than one congregation
            # mentioned (out of scope for the single-sender e-mail flow,
            # e.g. a bishop listing several churches at once) - always
            # manual review, never guess which one the fields belong to.
            await self._save_message(
                inbound,
                resolution="ambiguous",
                sender_person_id=precheck.person.id if precheck.person else None,
                tenant_id=None,
                extraction=extraction,
            )
            return

        entry = extraction.congregations[0]
        final = await self._resolver.resolve(inbound.from_address, entry.name, tenants, name_slugs)

        if final.kind != "matched_by_name":
            await self._save_message(
                inbound,
                resolution=final.kind,
                sender_person_id=final.person.id if final.person else None,
                tenant_id=final.tenant_id,
                extraction=extraction,
            )
            return

        assert final.person is not None and final.tenant_id is not None
        diff = await build_field_diff(entry, final.tenant_id, self._congregation_repo, self._church_repo)
        await self._resolve_and_maybe_apply(inbound, extraction, final, diff, tenant_names.get(final.tenant_id, ""))

    async def _resolve_and_maybe_apply(
        self,
        inbound: InboundEmail,
        extraction: ExtractionResult,
        final: SenderResolution,
        diff: FieldDiff,
        church_name: str,
    ) -> None:
        assert final.person is not None and final.tenant_id is not None
        changed = diff.changed_keys()

        if not changed:
            await self._save_message(inbound, resolution="matched_by_name", sender_person_id=final.person.id, tenant_id=final.tenant_id, extraction=extraction)
            return

        # Hard, free-to-check gates before spending an AI call: anti-spoofing
        # (SPF/DKIM/DMARC all pass) and, if any contact field changed, that
        # the sender is editing *their own* contact record - never someone
        # else's, even within a church they're otherwise authorized for.
        auth_pass = inbound.auth_spf == "pass" and inbound.auth_dkim == "pass" and inbound.auth_dmarc == "pass"
        contact_changed = any(FIELD_GROUPS[key] == "contact" for key in changed)
        sender_owns_contact = diff.matched_assignment is not None and diff.matched_assignment.person_id == final.person.id
        structurally_eligible = auth_pass and (not contact_changed or sender_owns_contact)

        verification_score: float | None = None
        verification_reasoning: str | None = None
        auto_apply = False

        if structurally_eligible:
            provider = OpenRouterProvider()

            # sender_context deliberately omits the sender's name: it's PII
            # resolved from the database (the sender is identified by e-mail
            # header, not by a name necessarily present in the message body),
            # so it would be new exposure to the external AI provider beyond
            # what's already in raw_text. The identity-plausibility judgment
            # the name used to support is covered locally instead (see
            # _signature_mentions_sender).
            sender_role = (assignment_title(diff.matched_assignment) if diff.matched_assignment else None) or "brak przypisanej funkcji"
            signature_note = "podpis/treść maila wygląda na zgodny ze znanym nadawcą" if _signature_mentions_sender(inbound.text_body, _person_label(final.person)) else "nie wykryto w treści maila wyraźnego podpisu pasującego do znanego nadawcy"
            sender_context = f"Rola: {sender_role}, zbór: {church_name}. Sygnał lokalny: {signature_note}."

            # diff_summary keeps the *new* values (they're already present in
            # raw_text below, which the AI extracted them from — redacting
            # them here would cost detection quality for no privacy benefit)
            # but replaces the *old* value with a presence/absence marker:
            # unlike the new values, the old value is genuinely new PII from
            # the database that isn't otherwise in this request.
            diff_summary = "\n".join(
                f"- {FIELD_LABELS[key]}: {'miało wcześniej wartość' if diff.old_values[key] else 'było puste'} -> "
                f"nowa wartość: {diff.new_values[key]} [format: {'poprawny' if new_value_format_plausible(key, diff.new_values[key]) else 'budzi wątpliwości'}]"
                for key in changed
            )

            verification = await provider.verify_extraction(inbound.text_body, sender_context, diff_summary)
            verification_score = verification.trust_score
            verification_reasoning = verification.reasoning
            threshold = get_settings().email_import.trust_auto_apply_threshold
            auto_apply = verification.trust_score >= threshold

        if not auto_apply:
            await self._save_message(
                inbound,
                resolution="matched_by_name",
                sender_person_id=final.person.id,
                tenant_id=final.tenant_id,
                extraction=extraction,
                verification_score=verification_score,
                verification_reasoning=verification_reasoning,
            )
            return

        assert verification_score is not None and verification_reasoning is not None
        await self._apply_and_log(inbound, extraction, final, diff, changed, church_name, verification_score, verification_reasoning)

    async def _apply_and_log(
        self,
        inbound: InboundEmail,
        extraction: ExtractionResult,
        final: SenderResolution,
        diff: FieldDiff,
        changed: list[str],
        church_name: str,
        trust_score: float,
        reasoning: str,
    ) -> None:
        assert final.person is not None and final.tenant_id is not None
        values = {key: diff.new_values[key] for key in changed}
        contact_person_id = diff.matched_assignment.id if diff.matched_assignment else None

        # Apply first, log second: if this raises, nothing (message row
        # included) gets persisted, so the next poll retries the whole
        # e-mail from scratch instead of leaving a misleading "handled" row
        # that dedup would otherwise skip forever.
        import_service = CongregationImportService(self.db)
        await import_service.apply_fields(final.tenant_id, values, contact_person_id)

        actor_label = f"{_person_label(final.person)} (automatycznie, AI {trust_score:.2f})"

        message = await self._save_message(
            inbound,
            resolution="matched_by_name",
            sender_person_id=final.person.id,
            tenant_id=final.tenant_id,
            extraction=extraction,
            verification_score=trust_score,
            verification_reasoning=reasoning,
            status="auto_applied",
        )

        for key in changed:
            self.db.add(
                CongregationChangeLogDB(
                    id=generate_id(),
                    tenant_id=final.tenant_id,
                    section=FIELD_GROUPS[key],
                    field=key,
                    old_value=diff.old_values[key],
                    new_value=diff.new_values[key],
                    source="email_auto",
                    actor_label=actor_label,
                    actor_person_id=final.person.id,
                    email_import_message_id=message.id,
                )
            )
        await self.db.commit()
        await self._congregation_repo.touch_last_updated(final.tenant_id, actor_label)

        await self._notify_admin(final, church_name, inbound, changed, diff, trust_score, reasoning)

    async def _notify_admin(
        self,
        final: SenderResolution,
        church_name: str,
        inbound: InboundEmail,
        changed: list[str],
        diff: FieldDiff,
        trust_score: float,
        reasoning: str,
    ) -> None:
        assert final.person is not None
        admin_email = get_settings().security.superadmin_email
        if not admin_email:
            logger.warning("SUPERADMIN_EMAIL not configured; skipping auto-apply notification")
            return

        changes = [{"label": FIELD_LABELS[key], "old_value": diff.old_values[key], "new_value": diff.new_values[key]} for key in changed]
        try:
            await get_email_service().send_email(
                to=admin_email,
                subject=f"Automatyczna aktualizacja danych zboru: {church_name}",
                template_name="email_import_auto_applied",
                context={
                    "church_name": church_name,
                    "sender_label": _person_label(final.person),
                    "sender_email": inbound.from_address,
                    "trust_score": f"{trust_score:.2f}",
                    "changes": changes,
                    "reasoning": reasoning,
                },
            )
        except Exception:
            logger.exception("Failed to send auto-apply admin notification for tenant %s", final.tenant_id)

    async def _save_message(
        self,
        inbound: InboundEmail,
        *,
        resolution: str,
        sender_person_id: str | None,
        tenant_id: str | None,
        extraction: ExtractionResult | None,
        verification_score: float | None = None,
        verification_reasoning: str | None = None,
        status: str = "pending",
    ) -> EmailImportMessageDB:
        message = EmailImportMessageDB(
            id=generate_id(),
            message_id=inbound.message_id,
            raw_from=inbound.from_address,
            sender_person_id=sender_person_id,
            resolved_tenant_id=tenant_id,
            resolution=resolution,
            auth_spf=inbound.auth_spf,
            auth_dkim=inbound.auth_dkim,
            auth_dmarc=inbound.auth_dmarc,
            extraction_json=extraction.model_dump_json() if extraction else None,
            verification_score=verification_score,
            verification_reasoning=verification_reasoning,
            status=status,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
