"""Country codes and province validation for congregation addresses."""

import pytest
from pydantic import ValidationError

from app.modules.congregations.geo import (
    DEFAULT_COUNTRY,
    POLISH_PROVINCES,
    is_valid_province,
)
from app.modules.congregations.schemas import AddressCreateRequest


def test_poland_has_sixteen_voivodeships() -> None:
    assert len(POLISH_PROVINCES) == 16
    assert len(set(POLISH_PROVINCES)) == 16


def test_province_slugs_are_ascii_so_they_survive_urls_and_exports() -> None:
    for province in POLISH_PROVINCES:
        assert province.isascii(), province
        assert province == province.lower()


@pytest.mark.parametrize("province", ["mazowieckie", "dolnoslaskie", None])
def test_known_polish_province_is_valid(province: str | None) -> None:
    assert is_valid_province("PL", province)


def test_unknown_polish_province_is_rejected() -> None:
    assert not is_valid_province("PL", "mazowsze")
    # A display name is not a slug.
    assert not is_valid_province("PL", "dolnośląskie")


def test_country_without_a_subdivision_list_accepts_only_no_province() -> None:
    assert is_valid_province("DE", None)
    assert not is_valid_province("DE", "bayern")


def test_address_defaults_to_poland() -> None:
    address = AddressCreateRequest(city="Warszawa")
    assert address.country == DEFAULT_COUNTRY == "PL"


def test_address_rejects_a_country_name() -> None:
    with pytest.raises(ValidationError):
        AddressCreateRequest(city="Warszawa", country="Poland")


def test_address_rejects_a_lowercase_country_code() -> None:
    with pytest.raises(ValidationError):
        AddressCreateRequest(city="Warszawa", country="pl")


def test_address_rejects_a_province_from_another_country() -> None:
    with pytest.raises(ValidationError):
        AddressCreateRequest(city="Marktredwitz", country="DE", province="mazowieckie")


def test_address_accepts_a_matching_country_and_province() -> None:
    address = AddressCreateRequest(city="Wrocław", country="PL", province="dolnoslaskie")
    assert address.province == "dolnoslaskie"
