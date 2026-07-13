"""Orchestrates polling the clergy e-mail update mailbox.

Phase 3 (docs/plans/2026-07-13--clergy-email-updates.md): fetch unseen mail,
resolve the sender and target congregation, run the existing AI extraction
pipeline, and land the result in the `email_import_messages` review queue.
Phase 4 adds the second AI verification pass and the auto-apply gate on top
of this — nothing here writes to congregation data yet.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.config import get_settings
from app.modules.ai.provider import OpenRouterProvider
from app.modules.ai.schemas import ExtractionResult
from app.modules.churches.slug_utils import slugify
from app.modules.congregations.email_import_db_models import EmailImportMessageDB
from app.modules.congregations.imap_client import ImapClient, InboundEmail
from app.modules.congregations.sender_resolver import SenderResolver
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository

logger = logging.getLogger(__name__)


@dataclass
class PollResult:
    fetched: int = 0
    processed: int = 0
    skipped_duplicate: int = 0


class EmailImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._resolver = SenderResolver(db)
        self._tenant_repo = TenantRepository(db)

    async def poll_and_process(self) -> PollResult:
        settings = get_settings().email_import
        if not settings.enabled:
            logger.info("Email import disabled (EMAIL_IMPORT_ENABLED=false); skipping poll")
            return PollResult()

        with ImapClient(settings) as client:
            emails = await asyncio.to_thread(client.fetch_unseen)

            tenants = await self._tenant_repo.list_all()
            name_slugs = {t.id: slugify(t.name) for t in tenants}
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
                    logger.exception("Failed processing inbound e-mail from %s; leaving unseen for retry", inbound.from_address)
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

        entry_name = extraction.congregations[0].name
        final = await self._resolver.resolve(inbound.from_address, entry_name, tenants, name_slugs)

        await self._save_message(
            inbound,
            resolution=final.kind,
            sender_person_id=final.person.id if final.person else None,
            tenant_id=final.tenant_id,
            extraction=extraction,
        )

    async def _save_message(
        self,
        inbound: InboundEmail,
        *,
        resolution: str,
        sender_person_id: str | None,
        tenant_id: str | None,
        extraction: ExtractionResult | None,
    ) -> None:
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
            status="pending",
        )
        self.db.add(message)
        await self.db.commit()
