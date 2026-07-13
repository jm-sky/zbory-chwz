"""Fuzzy-matching a free-text congregation name/city against known tenants.

Shared by the pasted-text import (`import_service.py`) and the clergy e-mail
import sender resolver (`sender_resolver.py`) — both need to turn "Zbór w
Świebodzinie" into a tenant_id the same way.
"""

from rapidfuzz import fuzz, process

from app.modules.churches.slug_utils import slugify
from app.modules.tenants.db_models import TenantDB

# Below this rapidfuzz score (0-100), a name is treated as having no match
# rather than risking a wrong auto-match (see docs/issues/2026-07-10--018--
# congregation-address-data-quality.md).
MATCH_THRESHOLD = 80.0


def match_tenant_by_name(
    detected_name: str,
    tenants: list[TenantDB],
    name_slugs: dict[str, str],
) -> tuple[str | None, str | None, float]:
    """Returns (tenant_id, matched_name, confidence) or (None, None, score) if no confident match."""
    if not name_slugs:
        return None, None, 0.0

    match = process.extractOne(slugify(detected_name), name_slugs, scorer=fuzz.WRatio)
    if match is None:
        return None, None, 0.0

    _, score, matched_tenant_id = match
    if score < MATCH_THRESHOLD:
        return None, None, score

    matched_name = next(t.name for t in tenants if t.id == matched_tenant_id)
    return matched_tenant_id, matched_name, score
