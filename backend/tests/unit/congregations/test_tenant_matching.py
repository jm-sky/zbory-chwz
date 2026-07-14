"""Tests for fuzzy tenant-name matching, including the preposition-stripping
normalization that lets "Zbór Warszawa" and "Zbór w Warszawie" match."""

from app.modules.congregations.tenant_matching import match_slug, match_tenant_by_name
from app.modules.tenants.db_models import TenantDB


def _tenant(tenant_id: str, name: str) -> TenantDB:
    return TenantDB(id=tenant_id, name=name, status="published", owner_id="owner")


def test_match_slug_strips_standalone_preposition_tokens() -> None:
    assert match_slug("Zbór w Warszawie") == "zbor-warszawie"
    assert match_slug("Zbór we Wrocławiu") == "zbor-wroclawiu"
    assert match_slug("Zbór Warszawa") == "zbor-warszawa"


def test_match_tenant_by_name_tolerates_preposition_variant() -> None:
    tenants = [_tenant("t1", "Zbór w Warszawie"), _tenant("t2", "Zbór w Poznaniu")]
    name_slugs = {t.id: match_slug(t.name) for t in tenants}

    tenant_id, matched_name, confidence = match_tenant_by_name("Zbór Warszawa", tenants, name_slugs)

    assert tenant_id == "t1"
    assert matched_name == "Zbór w Warszawie"
    assert confidence >= 80.0


def test_match_tenant_by_name_does_not_confuse_different_cities() -> None:
    tenants = [_tenant("t1", "Zbór w Warszawie"), _tenant("t2", "Zbór we Wrocławiu")]
    name_slugs = {t.id: match_slug(t.name) for t in tenants}

    tenant_id, _matched_name, _confidence = match_tenant_by_name("Zbór Gdańsk", tenants, name_slugs)

    assert tenant_id is None
