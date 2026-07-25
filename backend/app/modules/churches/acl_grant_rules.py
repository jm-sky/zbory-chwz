"""ACL grant rules for service assignments and role elevation."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.modules.auth.models import User
from app.modules.churches.acl_seed import ELEVATED_ROLE_NAMES, Permission
from app.modules.churches.db_models import ServiceTypeDB
from app.modules.churches.permission_service import PermissionService

Scope = tuple[str, str]


def required_permission_for_service_type(service_type: ServiceTypeDB | None) -> tuple[str, Scope | None]:
    """Return (permission, required_scope) for assigning this service type."""
    role = service_type.suggested_role if service_type else None
    if role in {"bishop", "regional_bishop"}:
        return Permission.SERVICES_MANAGE, ("community", "__placeholder__")
    if role == "pastor":
        return Permission.SERVICES_MANAGE, None
    return Permission.PEOPLE_MANAGE, None


async def assert_can_assign_service_type(
    permission_service: PermissionService,
    user: User,
    church_scope: Scope,
    service_type: ServiceTypeDB | None,
    *,
    community_id: str,
) -> None:
    permission, required_scope = required_permission_for_service_type(service_type)
    if required_scope and required_scope[0] == "community":
        check_scope: Scope = ("community", community_id)
    else:
        check_scope = church_scope

    if not await permission_service.resolve(user, permission, check_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def assert_can_grant_role(
    permission_service: PermissionService,
    user: User,
    role_name: str,
    grant_scope: Scope,
    *,
    community_id: str,
) -> None:
    if role_name not in ELEVATED_ROLE_NAMES and role_name not in {"pastor", "diacon", "branch_responsible"}:
        return

    if role_name in ELEVATED_ROLE_NAMES:
        if not (user.isAdmin or user.isOwner):
            if not await permission_service.resolve(
                user,
                Permission.SERVICES_MANAGE,
                ("community", community_id),
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Only admins may grant the '{role_name}' role",
                )
        return

    if not await permission_service.resolve(user, Permission.SERVICES_MANAGE, grant_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    granter_perms = await permission_service.role_permissions_in_scope(user, grant_scope)
    role_perms = await _role_permissions_by_name(permission_service, role_name)
    if not role_perms.issubset(granter_perms) and not (user.isAdmin or user.isOwner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot grant a role with permissions you do not hold",
        )


async def _role_permissions_by_name(permission_service: PermissionService, role_name: str) -> set[str]:
    from sqlalchemy import select

    from app.modules.churches.acl_models import RoleDB, RolePermissionDB

    db = permission_service.db
    result = await db.execute(select(RoleDB).where(RoleDB.name == role_name))
    role = result.scalar_one_or_none()
    if not role:
        return set()
    perm_result = await db.execute(select(RolePermissionDB.permission).where(RolePermissionDB.role_id == role.id))
    return {row[0] for row in perm_result.all()}
