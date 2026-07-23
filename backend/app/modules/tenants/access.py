"""Shared authorization helpers for tenant-scoped resources."""

from fastapi import HTTPException, status

from app.modules.auth.models import User
from app.modules.tenants.repositories import TenantRepository


async def verify_tenant_access(
    tenant_id: str,
    current_user: User,
    tenant_repo: TenantRepository,
) -> None:
    """Raise 404 when the tenant is unknown, 403 when the user may not touch it.

    Access is granted to members of the tenant and to global admins/owners.
    """
    tenant = await tenant_repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    if current_user.isAdmin or current_user.isOwner:
        return

    memberships = await tenant_repo.list_for_user(current_user.id)
    if any(membership.tenant_id == tenant_id for _, membership in memberships):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied",
    )
