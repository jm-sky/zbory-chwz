"""Filtering and church/person classification for imported Google contacts.

Implements decisions #3 and #4 from docs/plans/2026-07-10--google-contacts-sync.md:
- filter: case-insensitive text search for "zbór"/"chwz" in name, organization, notes
- classification: heuristic only — a contact with no first/last name and only
  an "Organization" field is a church; a contact with a first/last name is a
  person. Callers must still let the admin correct this on the mapping screen.
"""

from typing import Literal

FilterKeyword = Literal["zbór", "chwz"]
FILTER_KEYWORDS: tuple[str, ...] = ("zbór", "chwz")

ContactType = Literal["church", "person"]


def _searchable_text(contact: dict) -> str:
    parts: list[str] = []
    for name in contact.get("names", []) or []:
        parts.append(name.get("displayName") or "")
    for org in contact.get("organizations", []) or []:
        parts.append(org.get("name") or "")
    for bio in contact.get("biographies", []) or []:
        parts.append(bio.get("value") or "")
    return " ".join(parts)


def contact_matches_filter(contact: dict) -> bool:
    """True if the contact's name/organization/notes mention "zbór" or "chwz"."""

    haystack = _searchable_text(contact).casefold()
    return any(keyword in haystack for keyword in FILTER_KEYWORDS)


def classify_contact(contact: dict) -> ContactType:
    """Heuristic church-vs-person classification (subject to manual correction)."""

    for name in contact.get("names", []) or []:
        if name.get("givenName") or name.get("familyName"):
            return "person"

    if contact.get("organizations"):
        return "church"

    return "person"
