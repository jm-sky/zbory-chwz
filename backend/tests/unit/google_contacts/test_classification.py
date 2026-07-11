"""Tests for Google contact text-filtering and church/person classification.

Covers decisions #3 and #4 in docs/plans/2026-07-10--google-contacts-sync.md.
"""

from app.modules.google_contacts.classification import (
    classify_contact,
    contact_matches_filter,
)

CHURCH_CONTACT = {
    "organizations": [{"name": "Zbór CHWZ Warszawa"}],
}

PERSON_WITH_ORG_CONTACT = {
    "names": [{"displayName": "Jan Kowalski", "givenName": "Jan", "familyName": "Kowalski"}],
    "organizations": [{"name": "Zbór CHWZ Warszawa"}],
}

PERSON_CONTACT_NO_MATCH = {
    "names": [{"displayName": "Anna Nowak", "givenName": "Anna", "familyName": "Nowak"}],
}

NOTES_MATCH_CONTACT = {
    "names": [{"displayName": "Piotr Wiśniewski", "givenName": "Piotr", "familyName": "Wiśniewski"}],
    "biographies": [{"value": "Starszy zboru, kontakt do CHWZ"}],
}

CASE_INSENSITIVE_CONTACT = {
    "organizations": [{"name": "ZBÓR Poznań"}],
}


def test_contact_matches_filter_by_organization() -> None:
    assert contact_matches_filter(CHURCH_CONTACT) is True


def test_contact_matches_filter_by_notes() -> None:
    assert contact_matches_filter(NOTES_MATCH_CONTACT) is True


def test_contact_matches_filter_is_case_insensitive() -> None:
    assert contact_matches_filter(CASE_INSENSITIVE_CONTACT) is True


def test_contact_without_keyword_does_not_match() -> None:
    assert contact_matches_filter(PERSON_CONTACT_NO_MATCH) is False


def test_classify_contact_with_only_organization_is_church() -> None:
    assert classify_contact(CHURCH_CONTACT) == "church"


def test_classify_contact_with_name_is_person_even_with_organization() -> None:
    assert classify_contact(PERSON_WITH_ORG_CONTACT) == "person"


def test_classify_contact_with_no_name_and_no_organization_defaults_to_person() -> None:
    assert classify_contact({}) == "person"
