"""Admin review queue for clergy e-mail import proposals.

Complements email_import_service.py (which fetches/resolves/auto-applies):
this is the human-in-the-loop side for everything the auto-apply gate in
Phase 4 didn't clear. See docs/plans/2026-07-13--clergy-email-updates.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.ai.schemas import ExtractedCongregation, ExtractionResult
from app.modules.auth.models import User
from app.modules.churches.contact_sync import match_contact_assignment
from app.modules.churches.db_models import PersonDB
from app.modules.churches.repositories import ChurchRepository
from app.modules.congregations.email_import_db_models import (
    CongregationChangeLogDB,
    EmailImportMessageDB,
)
from app.modules.congregations.field_diff import (
    FIELD_GROUPS,
    FIELD_LABELS,
    build_field_diff,
)
from app.modules.congregations.import_service import CongregationImportService
from app.modules.congregations.repositories import CongregationRepository
from app.modules.congregations.schemas import (
    EmailImportApproveRequest,
    EmailImportInboxItem,
    EmailImportInboxListResponse,
    ImportApplyResponse,
    ImportFieldChange,
    ImportProposal,
)
from app.modules.tenants.repositories import TenantRepository


class EmailImportReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._congregation_repo = CongregationRepository(db)
        self._church_repo = ChurchRepository(db)
        self._tenant_repo = TenantRepository(db)

    async def list_pending(self) -> EmailImportInboxListResponse:
        result = await self.db.execute(select(EmailImportMessageDB).where(EmailImportMessageDB.status == "pending").order_by(EmailImportMessageDB.created_at.desc()))
        messages = list(result.scalars().all())

        items = []
        for message in messages:
            sender_label = await self._sender_label(message.sender_person_id)
            proposal = await self._build_proposal_if_resolved(message)
            items.append(
                EmailImportInboxItem(
                    message_id=message.id,
                    created_at=message.created_at,
                    raw_from=message.raw_from,
                    sender_label=sender_label,
                    resolution=message.resolution,  # type: ignore[arg-type]
                    auth_spf=message.auth_spf,
                    auth_dkim=message.auth_dkim,
                    auth_dmarc=message.auth_dmarc,
                    verification_score=message.verification_score,
                    verification_reasoning=message.verification_reasoning,
                    status=message.status,  # type: ignore[arg-type]
                    proposal=proposal,
                )
            )
        return EmailImportInboxListResponse(items=items)

    async def approve(self, message_id: str, request: EmailImportApproveRequest, *, reviewer: User) -> ImportApplyResponse:
        message = await self._get_pending_message(message_id)
        if not message.resolved_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This message has no resolved congregation to apply to - use the pasted-text import instead.",
            )

        entry = self._parse_single_entry(message)
        diff = await build_field_diff(
            entry,
            message.resolved_tenant_id,
            self._congregation_repo,
            self._church_repo,
        )

        values: dict[str, str | None] = {f.field: f.value for f in request.fields if f.apply}
        contact_person_id = diff.matched_assignment.id if diff.matched_assignment else None

        import_service = CongregationImportService(self.db)
        await import_service.apply_fields(message.resolved_tenant_id, values, contact_person_id)

        actor_label = f"{reviewer.name} (ręcznie zatwierdzone z e-maila)"
        batch_id = generate_id()
        for field_change in request.fields:
            if not field_change.apply:
                continue
            self.db.add(
                CongregationChangeLogDB(
                    id=generate_id(),
                    tenant_id=message.resolved_tenant_id,
                    batch_id=batch_id,
                    section=FIELD_GROUPS[field_change.field],
                    field=field_change.field,
                    old_value=diff.old_values.get(field_change.field),
                    new_value=field_change.value,
                    source="email_reviewed",
                    actor_label=actor_label,
                    actor_user_id=reviewer.id,
                    email_import_message_id=message.id,
                )
            )

        message.status = "approved"
        message.reviewed_by_user_id = reviewer.id
        message.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        if values:
            await self._congregation_repo.touch_last_updated(message.resolved_tenant_id, actor_label)

        return ImportApplyResponse(created=0, updated=1, skipped=0)

    async def reject(self, message_id: str, *, reviewer: User) -> None:
        message = await self._get_pending_message(message_id)
        message.status = "rejected"
        message.reviewed_by_user_id = reviewer.id
        message.reviewed_at = datetime.now(UTC)
        await self.db.commit()

    async def _get_pending_message(self, message_id: str) -> EmailImportMessageDB:
        result = await self.db.execute(select(EmailImportMessageDB).where(EmailImportMessageDB.id == message_id))
        message = result.scalar_one_or_none()
        if message is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        if message.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Message already {message.status}",
            )
        return message

    def _parse_single_entry(self, message: EmailImportMessageDB) -> ExtractedCongregation:
        if not message.extraction_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message has no extracted data",
            )
        extraction = ExtractionResult.model_validate_json(message.extraction_json)
        if len(extraction.congregations) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message does not resolve to exactly one congregation",
            )
        return extraction.congregations[0]

    async def _build_proposal_if_resolved(self, message: EmailImportMessageDB) -> ImportProposal | None:
        if not message.resolved_tenant_id or not message.extraction_json:
            return None

        extraction = ExtractionResult.model_validate_json(message.extraction_json)
        if len(extraction.congregations) != 1:
            return None
        entry = extraction.congregations[0]

        diff = await build_field_diff(
            entry,
            message.resolved_tenant_id,
            self._congregation_repo,
            self._church_repo,
        )
        field_keys = diff.changed_keys()
        fields = [
            ImportFieldChange(
                field=key,  # type: ignore[arg-type]
                label=FIELD_LABELS[key],
                group=FIELD_GROUPS[key],  # type: ignore[arg-type]
                old_value=diff.old_values[key],
                new_value=diff.new_values[key],
            )
            for key in field_keys
        ]

        tenant = await self._tenant_repo.get_tenant(message.resolved_tenant_id)
        matched_assignment = match_contact_assignment(entry.contact_name, diff.assignments)

        return ImportProposal(
            proposal_id=message.id,
            detected_name=entry.name,
            match_type="matched",
            tenant_id=message.resolved_tenant_id,
            matched_name=tenant.name if tenant else None,
            confidence=100.0,
            contact_context=None,
            contact_person_id=matched_assignment.id if matched_assignment else None,
            fields=fields,
        )

    async def _sender_label(self, person_id: str | None) -> str | None:
        if not person_id:
            return None
        result = await self.db.execute(select(PersonDB).where(PersonDB.id == person_id))
        person = result.scalar_one_or_none()
        if person is None:
            return None
        name = " ".join(part for part in (person.first_name, person.last_name) if part).strip()
        return name or person.email
