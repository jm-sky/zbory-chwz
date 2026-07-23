"""Some LLMs return the literal string "null" for a missing field instead of a
real JSON null, despite the strict schema - ExtractedCongregation must not let
that leak into the import diff as a visible "null" value."""

import pytest

from app.modules.ai.schemas import ExtractedCongregation


@pytest.mark.parametrize("placeholder", ["null", "NULL", "None", "n/a", "brak", "", "  "])
def test_null_like_string_is_normalized_to_none(placeholder: str) -> None:
    congregation = ExtractedCongregation(name="Zbór Warszawa", contact_email=placeholder)

    assert congregation.contact_email is None


def test_real_value_is_left_untouched() -> None:
    congregation = ExtractedCongregation(name="Zbór Warszawa", contact_email="jan@example.com")

    assert congregation.contact_email == "jan@example.com"


def test_null_like_string_is_normalized_on_every_nullable_field() -> None:
    congregation = ExtractedCongregation(
        name="Zbór Warszawa",
        street="null",
        city="null",
        postal_code="null",
        province="null",
        country="null",
        website="null",
        email="null",
        iban="null",
        contact_name="null",
        contact_title="null",
        contact_phone="null",
        contact_email="null",
    )

    assert congregation.model_dump(exclude={"name"}) == {
        "street": None,
        "city": None,
        "postal_code": None,
        "province": None,
        "country": None,
        "website": None,
        "email": None,
        "iban": None,
        "contact_name": None,
        "contact_title": None,
        "contact_phone": None,
        "contact_email": None,
    }
