"""Shared field-diff building for congregation import (pasted text and e-mail).

Both `import_service.py` (`_build_proposal`, admin paste-review) and
`email_import_service.py` (auto-apply gate) need to compare an AI-extracted
entry against the current DB state for a tenant the same way — this module
is the single place that comparison lives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.modules.ai.schemas import ExtractedCongregation
from app.modules.churches.contact_sync import assignment_contact_snapshot, match_contact_assignment
from app.modules.churches.db_models import ServiceAssignmentDB
from app.modules.churches.repositories import ChurchRepository
from app.modules.congregations.geo import DEFAULT_COUNTRY
from app.modules.congregations.repositories import CongregationRepository

FIELD_LABELS: dict[str, str] = {
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

# Labels for address fields the AI import/paste flow never extracts or diffs
# (so they must stay out of FIELD_LABELS - import_service.py iterates ALL of
# FIELD_LABELS' keys for a brand-new congregation and indexes matching
# new_values/old_values dicts, which only ever cover the fields above).
# Used only by the manual admin-edit change log (router.py get_change_log).
MANUAL_ONLY_FIELD_LABELS: dict[str, str] = {
    "latitude": "Szerokość geogr.",
    "longitude": "Długość geogr.",
}

ADDRESS_FIELDS = {"street", "city", "postal_code", "province", "country", "latitude", "longitude"}
CONTACT_FIELDS = {"contact_name", "contact_title", "contact_phone", "contact_email"}

FIELD_GROUPS: dict[str, str] = {
    **dict.fromkeys(ADDRESS_FIELDS, "address"),
    **dict.fromkeys(CONTACT_FIELDS, "contact"),
}

# Poland is the only country the app supports today (see geo.DEFAULT_COUNTRY),
# so a phone number without a country code is assumed to be a Polish one.
_DEFAULT_PHONE_COUNTRY_CODE = "48"

_EMAIL_FORMAT_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def new_value_format_plausible(field_key: str, value: str | None) -> bool:
    """Cheap structural check on a proposed new value, used as a signal for
    the AI trust-verification prompt (see email_import_service.py) instead of
    re-sending the value a second time for the model to eyeball — obviously
    malformed data (not a phone/email shape at all) is a spam/junk tell the
    model doesn't need the raw value to catch."""
    if value is None:
        return True
    if field_key == "contact_phone":
        normalized = normalize_phone(value)
        return normalized is not None and len(re.sub(r"\D", "", normalized)) >= 7
    if field_key == "contact_email":
        return bool(_EMAIL_FORMAT_RE.match(value.strip()))
    return True


def normalize_phone(value: str | None) -> str | None:
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


@dataclass
class FieldDiff:
    new_values: dict[str, str | None]
    old_values: dict[str, str | None]
    assignments: list[ServiceAssignmentDB] = field(default_factory=list)
    matched_assignment: ServiceAssignmentDB | None = None

    def changed_keys(self) -> list[str]:
        """Fields the AI extracted a non-null value for that actually differs from the current one.

        Iterates new_values' own keys (not FIELD_LABELS) so FIELD_LABELS can carry
        labels for fields this diff never populates (e.g. latitude/longitude, which
        the AI import flow doesn't extract) without a KeyError here.
        """
        return [key for key in self.new_values if self.new_values[key] is not None and self.new_values[key] != self.old_values[key]]


async def build_field_diff(
    entry: ExtractedCongregation,
    tenant_id: str | None,
    congregation_repo: CongregationRepository,
    church_repo: ChurchRepository,
) -> FieldDiff:
    current_address = await congregation_repo.get_address_by_tenant_id(tenant_id) if tenant_id else None
    assignments = await church_repo.list_service_assignments("church", tenant_id) if tenant_id else []
    matched_assignment = match_contact_assignment(entry.contact_name, assignments) if tenant_id else None
    current_contact = assignment_contact_snapshot(matched_assignment) if matched_assignment else None

    new_values = {
        "street": entry.street,
        "city": entry.city,
        "postal_code": entry.postal_code,
        "province": entry.province,
        "country": entry.country or DEFAULT_COUNTRY,
        "contact_name": entry.contact_name,
        "contact_title": entry.contact_title,
        "contact_phone": normalize_phone(entry.contact_phone),
        "contact_email": entry.contact_email,
    }
    old_values = {
        "street": current_address.street if current_address else None,
        "city": current_address.city if current_address else None,
        "postal_code": current_address.postal_code if current_address else None,
        "province": current_address.province if current_address else None,
        "country": current_address.country if current_address else None,
        "contact_name": (current_contact["contact_name"] if current_contact else None),
        "contact_title": (current_contact["contact_title"] if current_contact else None),
        "contact_phone": (normalize_phone(current_contact["contact_phone"]) if current_contact else None),
        "contact_email": (current_contact["contact_email"] if current_contact else None),
    }

    return FieldDiff(new_values=new_values, old_values=old_values, assignments=assignments, matched_assignment=matched_assignment)
