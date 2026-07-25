"""ACL role seeds and helpers."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.churches.acl_models import RoleDB, RolePermissionDB

PASTORAL_ROLE_NAMES = frozenset({"bishop", "regional_bishop", "pastor", "diacon"})

ELEVATED_ROLE_NAMES = frozenset({"bishop", "regional_bishop"})


class Permission(StrEnum):
    CHURCH_VIEW = "church.view"
    CHURCH_VIEW_PASTORAL = "church.view_pastoral"
    CHURCH_EDIT = "church.edit"
    CHURCH_CREATE = "church.create"
    CHURCH_DELETE = "church.delete"
    CHURCH_PUBLISH = "church.publish"
    CHURCH_MOVE_REGION = "church.move_region"
    SERVICES_MANAGE = "services.manage"
    PEOPLE_MANAGE = "people.manage"
    BRANCH_MANAGE = "branch.manage"
    EVENTS_MANAGE = "events.manage"
    DOCUMENTS_MANAGE = "documents.manage"


ROLE_SEED: list[tuple[str, str, list[str]]] = [
    (
        "bishop",
        "community",
        [
            Permission.CHURCH_VIEW,
            Permission.CHURCH_VIEW_PASTORAL,
            Permission.CHURCH_EDIT,
            Permission.CHURCH_CREATE,
            Permission.CHURCH_DELETE,
            Permission.CHURCH_PUBLISH,
            Permission.CHURCH_MOVE_REGION,
            Permission.SERVICES_MANAGE,
            Permission.PEOPLE_MANAGE,
            Permission.BRANCH_MANAGE,
        ],
    ),
    (
        "regional_bishop",
        "region",
        [
            Permission.CHURCH_VIEW,
            Permission.CHURCH_VIEW_PASTORAL,
            Permission.CHURCH_EDIT,
            Permission.CHURCH_CREATE,
            Permission.CHURCH_PUBLISH,
            Permission.SERVICES_MANAGE,
            Permission.PEOPLE_MANAGE,
            Permission.BRANCH_MANAGE,
        ],
    ),
    (
        "pastor",
        "church",
        [
            Permission.CHURCH_VIEW,
            Permission.CHURCH_VIEW_PASTORAL,
            Permission.CHURCH_EDIT,
            Permission.CHURCH_PUBLISH,
            Permission.PEOPLE_MANAGE,
            Permission.BRANCH_MANAGE,
            Permission.EVENTS_MANAGE,
        ],
    ),
    (
        "diacon",
        "church",
        [
            Permission.CHURCH_VIEW,
            Permission.CHURCH_VIEW_PASTORAL,
            Permission.CHURCH_EDIT,
            Permission.PEOPLE_MANAGE,
            Permission.EVENTS_MANAGE,
        ],
    ),
    (
        "branch_responsible",
        "branch",
        [
            Permission.CHURCH_VIEW,
            Permission.BRANCH_MANAGE,
        ],
    ),
]

ROLE_SCOPE_FOR_CHURCH: dict[str, str] = {
    "bishop": "community",
    "regional_bishop": "region",
    "pastor": "church",
    "diacon": "church",
    "branch_responsible": "branch",
}


async def ensure_acl_roles(db: AsyncSession) -> dict[str, RoleDB]:
    by_name: dict[str, RoleDB] = {}
    seeded_names: set[str] = set()
    for name, scope_type, permissions in ROLE_SEED:
        seeded_names.add(name)
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

        desired = set(permissions)
        existing_result = await db.execute(select(RolePermissionDB).where(RolePermissionDB.role_id == role.id))
        existing_rows = list(existing_result.scalars().all())
        existing_perms = {row.permission for row in existing_rows}

        for perm in desired - existing_perms:
            db.add(
                RolePermissionDB(
                    id=generate_id(),
                    role_id=role.id,
                    permission=perm,
                )
            )
        for row in existing_rows:
            if row.permission not in desired:
                await db.delete(row)

        by_name[name] = role

    await db.flush()
    return by_name


def resolve_acl_scope(
    role_name: str,
    *,
    church_id: str,
    community_id: str,
    region_id: str | None,
    branch_id: str | None = None,
) -> tuple[str, str] | None:
    scope_type = ROLE_SCOPE_FOR_CHURCH.get(role_name)
    if not scope_type:
        return None
    if scope_type == "branch":
        if not branch_id:
            return None
        return scope_type, branch_id
    if scope_type == "church":
        return scope_type, church_id
    if scope_type == "community":
        return scope_type, community_id
    if scope_type == "region":
        if not region_id:
            return None
        return scope_type, region_id
    return None
