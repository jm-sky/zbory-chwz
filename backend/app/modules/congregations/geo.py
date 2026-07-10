"""Geographic constants for congregation addresses.

Countries are stored as ISO 3166-1 alpha-2 codes ("PL", "DE") so the UI can
render a localized name via `Intl.DisplayNames` without translation files.

Provinces are stored as ASCII slugs. Only Poland has a defined subdivision
list today; addresses in other countries keep `province = NULL`.
"""

DEFAULT_COUNTRY = "PL"

COUNTRY_CODE_PATTERN = r"^[A-Z]{2}$"

# ISO 3166-2:PL — the 16 Polish voivodeships, as ASCII slugs.
POLISH_PROVINCES: tuple[str, ...] = (
    "dolnoslaskie",
    "kujawsko-pomorskie",
    "lubelskie",
    "lubuskie",
    "lodzkie",
    "malopolskie",
    "mazowieckie",
    "opolskie",
    "podkarpackie",
    "podlaskie",
    "pomorskie",
    "slaskie",
    "swietokrzyskie",
    "warminsko-mazurskie",
    "wielkopolskie",
    "zachodniopomorskie",
)

PROVINCES_BY_COUNTRY: dict[str, tuple[str, ...]] = {
    "PL": POLISH_PROVINCES,
}


def is_valid_province(country: str, province: str | None) -> bool:
    """A province must belong to its country's subdivision list, when one exists."""
    if province is None:
        return True
    known = PROVINCES_BY_COUNTRY.get(country)
    if known is None:
        return False
    return province in known
