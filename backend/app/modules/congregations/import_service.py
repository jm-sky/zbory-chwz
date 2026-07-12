"""Business logic for importing congregation address/contact data from free text.

Flow: AI extracts structured entries from pasted notes -> fuzzy-match each
entry's name against existing tenants -> build a field-by-field diff for
admin review -> apply only the fields the admin explicitly accepted.
"""

import re
import uuid

from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.provider import OpenRouterProvider
from app.modules.ai.schemas import ExtractedCongregation
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.slug_utils import slugify
from app.modules.congregations.db_models import CongregationContactPersonDB
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
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository

# Below this rapidfuzz score (0-100), a name is treated as having no match
# rather than risking a wrong auto-match (see docs/issues/...--018--...).
_MATCH_THRESHOLD = 80.0

# Same idea for contact persons: a congregation can have several (e.g. two
# deacons), and blindly editing whichever one happens to be first would
# silently overwrite the wrong person's data.
_CONTACT_MATCH_THRESHOLD = 80.0

_FIELD_LABELS: dict[str, str] = {
    "street": "Ulica",
    "city": "Miasto",
    "postal_code": "Kod pocztowy",
    "province": "Województwo",
    "country": "Kraj",
    "contact_name": "Osoba kontaktowa",
    "contact_title": "Funkcja",
    "contact_phone": "Telefon",
    "contact_email": "E-mail",
}

_ADDRESS_FIELDS = {"street", "city", "postal_code", "province", "country"}
_CONTACT_FIELDS = {"contact_name", "contact_title", "contact_phone", "contact_email"}

_FIELD_GROUPS: dict[str, str] = {
    **dict.fromkeys(_ADDRESS_FIELDS, "address"),
    **dict.fromkeys(_CONTACT_FIELDS, "contact"),
}

# Poland is the only country the app supports today (see geo.DEFAULT_COUNTRY),
# so a phone number without a country code is assumed to be a Polish one.
_DEFAULT_PHONE_COUNTRY_CODE = "48"


def _normalize_phone(value: str | None) -> str | None:
    """Strip formatting and apply the default country code, so e.g. '668-292-049'
    and '+48 668 292 049' compare as the same number instead of a false diff."""
    if not value:
        return None
    digits = re.sub(r"[^\d+]", "", value)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = f"+{digits[2:]}"
    if not digits.startswith("+"):
        digits = f"+{_DEFAULT_PHONE_COUNTRY_CODE}{digits}"
    return digits


class CongregationImportService:
    """Extracts, matches, diffs and applies congregation data from pasted text."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._congregation_repo = CongregationRepository(db)
        self._tenant_repo = TenantRepository(db)

    async def analyze(self, raw_text: str) -> ImportAnalyzeResponse:
        provider = OpenRouterProvider()
        extraction = await provider.extract_congregations(raw_text)

        tenants = await self._tenant_repo.list_all()
        candidates = [ImportCandidateTenant(tenant_id=t.id, name=t.name) for t in tenants]
        name_slugs = {t.id: slugify(t.name) for t in tenants}

        proposals = [await self._build_proposal(entry, tenants, name_slugs) for entry in extraction.congregations]

        return ImportAnalyzeResponse(proposals=proposals, candidates=candidates)

    async def _build_proposal(
        self,
        entry: ExtractedCongregation,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> ImportProposal:
        tenant_id, matched_name, confidence = self._match_tenant(entry.name, tenants, name_slugs)
        match_type: str = "matched" if tenant_id else "new"

        current_address = await self._congregation_repo.get_address_by_tenant_id(tenant_id) if tenant_id else None
        current_contacts = await self._congregation_repo.get_contact_persons_by_tenant_id(tenant_id) if tenant_id else []
        current_contact = self._match_contact(entry.contact_name, current_contacts)

        new_values = {
            "street": entry.street,
            "city": entry.city,
            "postal_code": entry.postal_code,
            "province": entry.province,
            "country": entry.country or DEFAULT_COUNTRY,
            "contact_name": entry.contact_name,
            "contact_title": entry.contact_title,
            "contact_phone": _normalize_phone(entry.contact_phone),
            "contact_email": entry.contact_email,
        }
        old_values = {
            "street": current_address.street if current_address else None,
            "city": current_address.city if current_address else None,
            "postal_code": current_address.postal_code if current_address else None,
            "province": current_address.province if current_address else None,
            "country": current_address.country if current_address else None,
            "contact_name": current_contact.name if current_contact else None,
            "contact_title": current_contact.title if current_contact else None,
            "contact_phone": _normalize_phone(current_contact.phone) if current_contact else None,
            "contact_email": current_contact.email if current_contact else None,
        }

        if match_type == "new":
            # A brand-new congregation needs every field visible and editable
            # (e.g. city is required but the AI may not have found one).
            field_keys = list(_FIELD_LABELS)
        else:
            # For an existing congregation, only show what actually changed.
            field_keys = [key for key in _FIELD_LABELS if new_values[key] is not None and new_values[key] != old_values[key]]

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
            if current_contact is None and len(current_contacts) > 0:
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
            contact_person_id=current_contact.id if current_contact else None,
            fields=fields,
        )

    def _match_tenant(
        self,
        detected_name: str,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> tuple[str | None, str | None, float]:
        if not name_slugs:
            return None, None, 0.0

        match = process.extractOne(slugify(detected_name), name_slugs, scorer=fuzz.WRatio)
        if match is None:
            return None, None, 0.0

        _, score, matched_tenant_id = match
        if score < _MATCH_THRESHOLD:
            return None, None, score

        matched_name = next(t.name for t in tenants if t.id == matched_tenant_id)
        return matched_tenant_id, matched_name, score

    def _match_contact(
        self,
        detected_name: str | None,
        contacts: list[CongregationContactPersonDB],
    ) -> CongregationContactPersonDB | None:
        """Pick which existing contact person the extracted name refers to.

        A single existing contact is used as-is (matches the old behavior).
        With several, only a confident name match is used; an unclear match
        returns None so the caller creates a new contact instead of
        overwriting the wrong person.
        """
        if len(contacts) <= 1:
            return contacts[0] if contacts else None
        if not detected_name:
            return None

        name_slugs = {contact.id: slugify(contact.name) for contact in contacts}
        match = process.extractOne(slugify(detected_name), name_slugs, scorer=fuzz.WRatio)
        if match is None:
            return None

        _, score, matched_contact_id = match
        if score < _CONTACT_MATCH_THRESHOLD:
            return None

        return next(contact for contact in contacts if contact.id == matched_contact_id)

    async def apply(self, request: ImportApplyRequest, *, owner_user_id: str) -> ImportApplyResponse:
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

            await self._apply_fields(tenant_id, values, item.contact_person_id)

        return ImportApplyResponse(created=created, updated=updated, skipped=skipped)

    async def _apply_fields(self, tenant_id: str, values: dict[str, str | None], contact_person_id: str | None) -> None:
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

    async def _apply_contact_fields(self, tenant_id: str, values: dict[str, str | None], contact_person_id: str | None) -> None:
        contacts = await self._congregation_repo.get_contact_persons_by_tenant_id(tenant_id)
        if contact_person_id:
            existing_contact = next((c for c in contacts if c.id == contact_person_id), None)
        else:
            # No contact was pinned during analyze (e.g. an older client) -
            # fall back to the same confident-match-or-nothing logic rather
            # than guessing which of several contacts to overwrite.
            existing_contact = self._match_contact(values.get("contact_name"), contacts)

        name = values.get("contact_name") or (existing_contact.name if existing_contact else None)
        if not name:
            raise ValueError(f"Contact name is required to save a contact person for tenant {tenant_id}")

        if existing_contact:
            existing_contact.name = name
            if "contact_title" in values:
                existing_contact.title = values["contact_title"]
            if "contact_phone" in values:
                existing_contact.phone = _normalize_phone(values["contact_phone"])
            if "contact_email" in values:
                existing_contact.email = values["contact_email"]
            await self.db.commit()
        else:
            await self._congregation_repo.create_contact_person(
                tenant_id,
                name=name,
                title=values.get("contact_title"),
                phone=_normalize_phone(values.get("contact_phone")),
                email=values.get("contact_email"),
            )
