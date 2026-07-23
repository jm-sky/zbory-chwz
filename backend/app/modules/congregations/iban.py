"""IBAN normalization and validation.

The congregation address form accepts a bare Polish NRB (26 digits, no
country prefix) for entry convenience, but the database always stores the
full canonical IBAN (country prefix, no spaces, upper case) — display
formatting then branches on country (see src/shared/utils/formatIban.ts).
"""

import re

# IBAN length by ISO 3166-1 alpha-2 country code, per the SWIFT/ISO 13616
# IBAN registry. Countries not listed here are still accepted (SEPA is not
# the whole world) but only get the generic shape + checksum check below,
# not a length check.
IBAN_LENGTHS: dict[str, int] = {
    "AD": 24,
    "AE": 23,
    "AL": 28,
    "AT": 20,
    "AZ": 28,
    "BA": 20,
    "BE": 16,
    "BG": 22,
    "BH": 22,
    "BR": 29,
    "BY": 28,
    "CH": 21,
    "CR": 22,
    "CY": 28,
    "CZ": 24,
    "DE": 22,
    "DK": 18,
    "DO": 28,
    "EE": 20,
    "EG": 29,
    "ES": 24,
    "FI": 18,
    "FO": 18,
    "FR": 27,
    "GB": 22,
    "GE": 22,
    "GI": 23,
    "GL": 18,
    "GR": 27,
    "GT": 28,
    "HR": 21,
    "HU": 28,
    "IE": 22,
    "IL": 23,
    "IQ": 23,
    "IS": 26,
    "IT": 27,
    "JO": 30,
    "KW": 30,
    "KZ": 20,
    "LB": 28,
    "LC": 32,
    "LI": 21,
    "LT": 20,
    "LU": 20,
    "LV": 21,
    "LY": 25,
    "MC": 27,
    "MD": 24,
    "ME": 22,
    "MK": 19,
    "MR": 27,
    "MT": 31,
    "MU": 30,
    "NL": 18,
    "NO": 15,
    "PK": 24,
    "PL": 28,
    "PS": 29,
    "PT": 25,
    "QA": 29,
    "RO": 24,
    "RS": 22,
    "SA": 24,
    "SC": 31,
    "SE": 24,
    "SI": 19,
    "SK": 24,
    "SM": 27,
    "ST": 25,
    "SV": 28,
    "TL": 23,
    "TN": 24,
    "TR": 26,
    "UA": 29,
    "VA": 22,
    "VG": 24,
    "XK": 20,
}

# Length of a Polish NRB (national account number) without the "PL" prefix
# and its 2 checksum digits already merged in — i.e. IBAN_LENGTHS["PL"] - 2.
_PL_NRB_LENGTH = 26

_IBAN_SHAPE_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]+$")


def normalize_iban(raw: str) -> str:
    """Strip formatting and upper-case; bare Polish NRB digits get a "PL" prefix."""
    cleaned = re.sub(r"[\s-]", "", raw).upper()
    if cleaned.isdigit() and len(cleaned) == _PL_NRB_LENGTH:
        return f"PL{cleaned}"
    return cleaned


def is_valid_iban(iban: str) -> bool:
    """Mod-97 checksum (ISO 7064), plus a length check for known countries."""
    if not _IBAN_SHAPE_RE.match(iban):
        return False

    expected_length = IBAN_LENGTHS.get(iban[:2])
    if expected_length is not None and len(iban) != expected_length:
        return False

    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1
