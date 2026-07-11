"""Tests for mapping a raw People API contact into GoogleContactSuggestion."""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.modules.google_contacts.service import _to_suggestion

RAW_CONTACT = {
    "resourceName": "people/c1",
    "names": [{"displayName": "Jan Kowalski", "givenName": "Jan", "familyName": "Kowalski"}],
    "organizations": [{"name": "Zbór CHWZ Gdańsk"}],
    "emailAddresses": [{"value": "jan@example.com"}],
    "phoneNumbers": [{"value": "+48123456789"}],
    "addresses": [
        {
            "streetAddress": "Długa 1",
            "city": "Gdańsk",
            "postalCode": "80-001",
            "region": "pomorskie",
            "countryCode": "PL",
        }
    ],
}


def test_to_suggestion_maps_name_and_address_fields() -> None:
    suggestion = _to_suggestion(RAW_CONTACT)

    assert suggestion.firstName == "Jan"
    assert suggestion.lastName == "Kowalski"
    assert suggestion.organizationName == "Zbór CHWZ Gdańsk"
    assert suggestion.addressStreet == "Długa 1"
    assert suggestion.addressCity == "Gdańsk"
    assert suggestion.addressPostalCode == "80-001"
    assert suggestion.addressProvince == "pomorskie"
    assert suggestion.addressCountry == "PL"


def test_to_suggestion_handles_missing_address() -> None:
    suggestion = _to_suggestion({"resourceName": "people/c2"})

    assert suggestion.addressCity is None
    assert suggestion.firstName is None
