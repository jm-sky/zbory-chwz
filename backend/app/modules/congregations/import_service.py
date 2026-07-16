"""Business logic for importing congregation address/contact data from free text.

Flow: AI extracts structured entries from pasted notes -> fuzzy-match each
entry's name against existing tenants -> build a field-by-field diff for
admin review -> apply only the fields the admin explicitly accepted.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.provider import OpenRouterProvider
from app.modules.ai.schemas import ExtractedCongregation
from app.modules.churches.contact_sync import (
    assignment_contact_snapshot,
    load_service_types_by_slug,
    match_contact_assignment,
    resolve_service_type_for_title,
    split_person_name,
    upsert_primary_card_contact,
)
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import ServiceAssignmentCreateRequest, ServiceAssignmentUpdateRequest
from app.modules.congregations.field_diff import ADDRESS_FIELDS as _ADDRESS_FIELDS
from app.modules.congregations.field_diff import CONTACT_FIELDS as _CONTACT_FIELDS
from app.modules.congregations.field_diff import FIELD_GROUPS as _FIELD_GROUPS
from app.modules.congregations.field_diff import FIELD_LABELS as _FIELD_LABELS
from app.modules.congregations.field_diff import build_field_diff
from app.modules.congregations.field_diff import normalize_phone as _normalize_phone
from app.modules.congregations.geo import DEFAULT_COUNTRY, is_valid_province
from app.modules.congregations.repositories import CongregationRepository
from app.modules.congregations.schemas import (
    ImportAnalyzeResponse,
    ImportApplyRequest,
    ImportApplyResponse,
    ImportCandidateTenant,
    ImportFieldChange,
    ImportProposal,
)
from app.modules.congregations.tenant_matching import match_slug, match_tenant_by_name
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository


class CongregationImportService:
    """Extracts, matches, diffs and applies congregation data from pasted text."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._congregation_repo = CongregationRepository(db)
        self._tenant_repo = TenantRepository(db)
        self._church_repo = ChurchRepository(db)

    async def analyze(self, raw_text: str) -> ImportAnalyzeResponse:
        provider = OpenRouterProvider()
        extraction = await provider.extract_congregations(raw_text)

        tenants = await self._tenant_repo.list_all()
        candidates = [ImportCandidateTenant(tenant_id=t.id, name=t.name) for t in tenants]
        name_slugs = {t.id: match_slug(t.name) for t in tenants}

        proposals = [await self._build_proposal(entry, tenants, name_slugs) for entry in extraction.congregations]

        return ImportAnalyzeResponse(proposals=proposals, candidates=candidates)

    async def _build_proposal(
        self,
        entry: ExtractedCongregation,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> ImportProposal:
        tenant_id, matched_name, confidence = match_tenant_by_name(entry.name, tenants, name_slugs)
        match_type: str = "matched" if tenant_id else "new"

        diff = await build_field_diff(entry, tenant_id, self._congregation_repo, self._church_repo)
        new_values, old_values = diff.new_values, diff.old_values
        assignments, matched_assignment = diff.assignments, diff.matched_assignment

        if match_type == "new":
            # A brand-new congregation needs every field visible and editable
            # (e.g. city is required but the AI may not have found one).
            field_keys = list(_FIELD_LABELS)
        else:
            # For an existing congregation, only show what actually changed.
            field_keys = diff.changed_keys()

        fields = [
            ImportFieldChange(
                field=key,  # type: ignore[arg-type]
                label=_FIELD_LABELS[key],
                group=_FIELD_GROUPS[key],  # type: ignore[arg-type]
                old_value=old_values[key],
                new_value=new_values[key],
            )
            for key in field_keys
        ]

        contact_context = None
        if any(_FIELD_GROUPS[key] == "contact" for key in field_keys):
            context_name = new_values["contact_name"] or old_values["contact_name"]
            context_title = new_values["contact_title"] or old_values["contact_title"]
            if context_title and context_name:
                contact_context = f"{context_title}: {context_name}"
            else:
                contact_context = context_title or context_name
            if matched_assignment is None and len(assignments) > 0:
                # Couldn't confidently match one of several existing contacts,
                # so applying will create a new one rather than risk editing
                # the wrong person.
                contact_context = f"{contact_context} (nowa osoba)" if contact_context else "nowa osoba"

        return ImportProposal(
            proposal_id=str(uuid.uuid4()),
            detected_name=entry.name,
            match_type=match_type,  # type: ignore[arg-type]
            tenant_id=tenant_id,
            matched_name=matched_name,
            confidence=round(confidence, 1),
            contact_context=contact_context,
            contact_person_id=matched_assignment.id if matched_assignment else None,
            fields=fields,
        )

    async def apply(self, request: ImportApplyRequest, *, owner_user_id: str, actor_name: str) -> ImportApplyResponse:
        created = updated = skipped = 0

        for item in request.items:
            if item.action == "skip":
                skipped += 1
                continue

            values: dict[str, str | None] = {f.field: f.value for f in item.fields if f.apply}

            if item.action == "create":
                assert item.congregation_name is not None
                tenant, _ = await self._tenant_repo.create_tenant(
                    name=item.congregation_name,
                    description=None,
                    owner_user_id=owner_user_id,
                    status="draft",
                )
                await provision_church_for_tenant(self.db, tenant)
                await self.db.commit()
                tenant_id = tenant.id
                created += 1
            else:
                assert item.tenant_id is not None
                tenant_id = item.tenant_id
                updated += 1

            before_address, before_contact = await self._capture_before(tenant_id, values, item.contact_person_id)
            await self.apply_fields(tenant_id, values, item.contact_person_id)
            await self._log_manual_changes(tenant_id, values, before_address, before_contact, actor_name, owner_user_id)

        return ImportApplyResponse(created=created, updated=updated, skipped=skipped)

    async def _capture_before(
        self,
        tenant_id: str,
        values: dict[str, str | None],
        contact_person_id: str | None,
    ) -> tuple[dict[str, str | None], dict[str, str | None]]:
        """Snapshot current address/contact field values before apply_fields overwrites them, for change-log diffing."""
        existing_address = await self._congregation_repo.get_address_by_tenant_id(tenant_id)
        before_address = {field: (getattr(existing_address, field) if existing_address else None) for field in _ADDRESS_FIELDS}

        assignments = await self._church_repo.list_service_assignments("church", tenant_id)
        target = next((a for a in assignments if a.id == contact_person_id), None) if contact_person_id else match_contact_assignment(values.get("contact_name"), assignments)
        current_contact = assignment_contact_snapshot(target) if target else None
        before_contact: dict[str, str | None] = {field: (current_contact.get(field) if current_contact else None) for field in _CONTACT_FIELDS}
        before_contact["contact_phone"] = _normalize_phone(before_contact["contact_phone"])

        return before_address, before_contact

    async def _log_manual_changes(
        self,
        tenant_id: str,
        values: dict[str, str | None],
        before_address: dict[str, str | None],
        before_contact: dict[str, str | None],
        actor_name: str,
        actor_user_id: str,
    ) -> None:
        address_changes = {field: (before_address[field], values[field]) for field in _ADDRESS_FIELDS if field in values and values[field] != before_address[field]}
        contact_changes = {field: (before_contact[field], values[field]) for field in _CONTACT_FIELDS if field in values and values[field] != before_contact[field]}

        await self._congregation_repo.log_changes(
            tenant_id,
            section="address",
            changes=address_changes,
            source="import_paste",
            actor_label=actor_name,
            actor_user_id=actor_user_id,
        )
        await self._congregation_repo.log_changes(
            tenant_id,
            section="contact",
            changes=contact_changes,
            source="import_paste",
            actor_label=actor_name,
            actor_user_id=actor_user_id,
        )

    async def apply_fields(self, tenant_id: str, values: dict[str, str | None], contact_person_id: str | None) -> None:
        if _ADDRESS_FIELDS & values.keys():
            await self._apply_address_fields(tenant_id, values)

        if _CONTACT_FIELDS & values.keys():
            await self._apply_contact_fields(tenant_id, values, contact_person_id)

    async def _apply_address_fields(self, tenant_id: str, values: dict[str, str | None]) -> None:
        existing = await self._congregation_repo.get_address_by_tenant_id(tenant_id)

        def merged(key: str) -> str | None:
            if key in values:
                return values[key]
            return getattr(existing, key) if existing else None

        city = merged("city")
        if not city:
            raise ValueError(f"City is required to save an address for tenant {tenant_id}")

        country = merged("country") or DEFAULT_COUNTRY
        province = merged("province")
        if not is_valid_province(country, province):
            raise ValueError(f"{province!r} is not a province of {country}")

        await self._congregation_repo.create_or_update_address(
            tenant_id,
            street=merged("street"),
            city=city,
            postal_code=merged("postal_code"),
            province=province,
            country=country,
            status=existing.status if existing else "draft",
        )

    async def _apply_contact_fields(
        self,
        tenant_id: str,
        values: dict[str, str | None],
        contact_person_id: str | None,
    ) -> None:
        assignments = await self._church_repo.list_service_assignments("church", tenant_id)
        if contact_person_id:
            target = next((assignment for assignment in assignments if assignment.id == contact_person_id), None)
        else:
            # No contact was pinned during analyze (e.g. an older client) -
            # fall back to the same confident-match-or-nothing logic rather
            # than guessing which of several contacts to overwrite.
            target = match_contact_assignment(values.get("contact_name"), assignments)

        if target:
            current = assignment_contact_snapshot(target)
            name = values.get("contact_name") or current["contact_name"]
            if not name:
                raise ValueError(f"Contact name is required to save a service contact for tenant {tenant_id}")

            title = values.get("contact_title") if "contact_title" in values else current["contact_title"]
            phone = _normalize_phone(values["contact_phone"]) if "contact_phone" in values else current["contact_phone"]
            email = values.get("contact_email") if "contact_email" in values else current["contact_email"]
            first_name, last_name = split_person_name(name)
            service_types_by_slug = await load_service_types_by_slug(self._church_repo.db)
            service_type_id, custom_service_name = resolve_service_type_for_title(title, service_types_by_slug)

            update_payload: dict[str, object] = {}
            if "contact_name" in values or not values.get("contact_name"):
                update_payload["firstName"] = first_name
                update_payload["lastName"] = last_name
            if "contact_phone" in values:
                update_payload["phone"] = phone
            if "contact_email" in values:
                update_payload["email"] = email
            if "contact_title" in values:
                update_payload["serviceTypeId"] = service_type_id
                update_payload["customServiceName"] = custom_service_name

            await self._church_repo.update_service_assignment(
                "church",
                tenant_id,
                target.id,
                ServiceAssignmentUpdateRequest.model_validate(update_payload),
            )
            return

        name = values.get("contact_name")
        if not name:
            raise ValueError(f"Contact name is required to save a service contact for tenant {tenant_id}")

        if assignments:
            first_name, last_name = split_person_name(name)
            service_types_by_slug = await load_service_types_by_slug(self._church_repo.db)
            title = values.get("contact_title")
            service_type_id, custom_service_name = resolve_service_type_for_title(title, service_types_by_slug)
            if not service_type_id and not custom_service_name:
                custom_service_name = title or "Kontakt"

            phone = _normalize_phone(values.get("contact_phone"))
            email = values.get("contact_email")
            await self._church_repo.create_service_assignment(
                "church",
                tenant_id,
                ServiceAssignmentCreateRequest(
                    firstName=first_name,
                    lastName=last_name,
                    email=email,
                    phone=phone,
                    serviceTypeId=service_type_id,
                    customServiceName=custom_service_name,
                    showOnList=True,
                    profileVisibility="public",
                    phoneVisibility="public" if phone else "hidden",
                    emailVisibility="public" if email else "hidden",
                ),
            )
            return

        await upsert_primary_card_contact(
            self._church_repo,
            tenant_id,
            name=name,
            title=values.get("contact_title"),
            phone=_normalize_phone(values.get("contact_phone")),
            email=values.get("contact_email"),
            fields=set(values.keys()) & _CONTACT_FIELDS,
        )
