from app.modules.congregations.iban import is_valid_iban, normalize_iban

VALID_PL_IBAN = "PL61109010140000071219812874"
VALID_DE_IBAN = "DE89370400440532013000"


def test_normalize_adds_pl_prefix_to_bare_nrb() -> None:
    assert normalize_iban("61 1090 1014 0000 0712 1981 2874") == VALID_PL_IBAN


def test_normalize_strips_spaces_and_upper_cases() -> None:
    assert normalize_iban("de89 3704 0044 0532 0130 00") == VALID_DE_IBAN


def test_normalize_leaves_a_full_iban_untouched() -> None:
    assert normalize_iban(VALID_PL_IBAN) == VALID_PL_IBAN


def test_valid_polish_iban_passes_checksum() -> None:
    assert is_valid_iban(VALID_PL_IBAN) is True


def test_valid_foreign_iban_passes_checksum() -> None:
    assert is_valid_iban(VALID_DE_IBAN) is True


def test_iban_with_bad_checksum_is_rejected() -> None:
    assert is_valid_iban("PL61109010140000071219812875") is False


def test_iban_with_wrong_length_for_known_country_is_rejected() -> None:
    assert is_valid_iban("PL6110901014000007121981287") is False


def test_iban_with_invalid_shape_is_rejected() -> None:
    assert is_valid_iban("not-an-iban") is False
