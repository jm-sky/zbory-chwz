"""ACL role seeds and helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.churches.acl_models import RoleDB, RolePermissionDB

PASTORAL_ROLE_NAMES = frozenset({"bishop", "regional_bishop", "pastor", "diacon"})

ROLE_SEED: list[tuple[str, str, list[str]]] = [
    (
        "bishop",
        "community",
        [
            "church.view",
            "church.edit",
            "church.create",
            "church.move_region",
            "services.manage",
            "people.manage",
        ],
    ),
    (
        "regional_bishop",
        "region",
        ["church.view", "church.edit", "church.create", "services.manage", "people.manage"],
    ),
    (
        "pastor",
        "church",
        ["church.view", "church.edit", "people.manage", "events.manage"],
    ),
    (
        "diacon",
        "church",
        ["church.view", "church.edit", "people.manage", "events.manage"],
    ),
]

ROLE_SCOPE_FOR_CHURCH: dict[str, str] = {
    "bishop": "community",
    "regional_bishop": "region",
    "pastor": "church",
    "diacon": "church",
}


async def ensure_acl_roles(db: AsyncSession) -> dict[str, RoleDB]:
    by_name: dict[str, RoleDB] = {}
    for name, scope_type, permissions in ROLE_SEED:
        result = await db.execute(select(RoleDB).where(RoleDB.name == name))
        role = result.scalar_one_or_none()
        if not role:
            role = RoleDB(
                id=generate_id(),
                name=name,
                scope_type=scope_type,
            )
            db.add(role)
            await db.flush()
            for permission in permissions:
                db.add(
                    RolePermissionDB(
                        id=generate_id(),
                        role_id=role.id,
                        permission=permission,
                    )
                )
        by_name[name] = role
    await db.flush()
    return by_name


def resolve_acl_scope(
    role_name: str,
    *,
    church_id: str,
    community_id: str,
    region_id: str | None,
) -> tuple[str, str] | None:
    scope_type = ROLE_SCOPE_FOR_CHURCH.get(role_name)
    if not scope_type:
        return None
    if scope_type == "church":
        return scope_type, church_id
    if scope_type == "community":
        return scope_type, community_id
    if scope_type == "region":
        if not region_id:
            return None
        return scope_type, region_id
    return None
