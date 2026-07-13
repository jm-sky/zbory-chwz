"""Filtering and church/person classification for imported Google contacts.

Implements decisions #3 and #4 from docs/plans/2026-07-10--google-contacts-sync.md:
- filter: case-insensitive text search for configurable keywords (default
  "zbór"/"chwz") in name, organization, notes
- classification: heuristic only — a contact whose display name itself
  mentions one of the filter keywords is a church (Google sometimes parses a
  congregation's name into givenName/familyName, which would otherwise trick
  the name-based check below); otherwise a contact with a first/last name is
  a person, and a contact with no name but an "Organization" field is a
  church. Callers must still let the admin correct this on the mapping screen.
"""

from collections.abc import Sequence
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


def _display_name_text(contact: dict) -> str:
    return " ".join((name.get("displayName") or "") for name in contact.get("names", []) or [])


def contact_matches_filter(contact: dict, keywords: Sequence[str] = FILTER_KEYWORDS) -> bool:
    """True if the contact's name/organization/notes mention any of the keywords."""

    haystack = _searchable_text(contact).casefold()
    return any(keyword.casefold() in haystack for keyword in keywords)


def classify_contact(contact: dict, keywords: Sequence[str] = FILTER_KEYWORDS) -> ContactType:
    """Heuristic church-vs-person classification (subject to manual correction)."""

    display_name = _display_name_text(contact).casefold()
    if any(keyword.casefold() in display_name for keyword in keywords):
        return "church"

    for name in contact.get("names", []) or []:
        if name.get("givenName") or name.get("familyName"):
            return "person"

    if contact.get("organizations"):
        return "church"

    return "person"
