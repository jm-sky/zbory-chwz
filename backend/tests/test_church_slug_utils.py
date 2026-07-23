"""Tests for church slug utilities."""

from app.modules.churches.slug_utils import church_slug, city_slug, country_slug


def test_city_slug_polish() -> None:
    assert city_slug("Warszawa") == "warszawa"
    assert city_slug("Łódź") == "lodz"


def test_country_slug_poland() -> None:
    assert country_slug("Poland") == "polska"


def test_church_slug() -> None:
    assert church_slug("Zbór Przyce") == "zbor-przyce"
