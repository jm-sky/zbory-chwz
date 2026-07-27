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


async def _grant_role_denial_reason(
    permission_service: PermissionService,
    user: User,
    role_name: str,
    grant_scope: Scope,
    *,
    community_id: str,
) -> str | None:
    """Return why granting `role_name` at `grant_scope` would be denied, or None if allowed.

    Single source of truth shared by the write path (assert_can_grant_role /
    assert_can_revoke_role) and the read-only /churches/grantable-roles listing
    (can_grant_role, G0.4) — the UI must never diverge from what the API actually enforces.
    """
    if role_name not in ELEVATED_ROLE_NAMES and role_name not in {"pastor", "diacon", "branch_responsible"}:
        return None

    if role_name in ELEVATED_ROLE_NAMES:
        if user.isAdmin or user.isOwner:
            return None
        if await permission_service.resolve(user, Permission.SERVICES_MANAGE, ("community", community_id)):
            return None
        return f"Only admins may grant the '{role_name}' role"

    if not await permission_service.resolve(user, Permission.SERVICES_MANAGE, grant_scope):
        return "Access denied"

    if user.isAdmin or user.isOwner:
        return None

    granter_perms = await permission_service.role_permissions_in_scope(user, grant_scope)
    role_perms = await _role_permissions_by_name(permission_service, role_name)
    if not role_perms.issubset(granter_perms):
        return "Cannot grant a role with permissions you do not hold"
    return None


async def can_grant_role(
    permission_service: PermissionService,
    user: User,
    role_name: str,
    grant_scope: Scope,
    *,
    community_id: str,
) -> bool:
    """Bool-returning variant of assert_can_grant_role for read-only listings (grantable-roles)."""
    reason = await _grant_role_denial_reason(permission_service, user, role_name, grant_scope, community_id=community_id)
    return reason is None


async def assert_can_grant_role(
    permission_service: PermissionService,
    user: User,
    role_name: str,
    grant_scope: Scope,
    *,
    community_id: str,
) -> None:
    reason = await _grant_role_denial_reason(permission_service, user, role_name, grant_scope, community_id=community_id)
    if reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)


async def assert_can_revoke_role(
    permission_service: PermissionService,
    user: User,
    role_name: str,
    grant_scope: Scope,
    *,
    community_id: str,
) -> None:
    """Revoking a role requires the same authority as granting it (§ Reguły bezpieczeństwa #3
    in the governance UI plan) — otherwise a low-privileged actor could strip a role from
    someone above them instead of merely being unable to grant it."""
    await assert_can_grant_role(permission_service, user, role_name, grant_scope, community_id=community_id)


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
