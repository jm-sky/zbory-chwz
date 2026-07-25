"""Shared authorization helpers for tenant-scoped resources."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.modules.auth.models import User
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.seed_data import CHWZ_ORG_TENANT_NAME
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository


async def verify_tenant_access(
    tenant_id: str,
    current_user: User,
    tenant_repo: TenantRepository,
    permission_service: PermissionService,
    church_repo: ChurchRepository,
    *,
    permission: str = "church.edit",
) -> None:
    """Raise 404 when the tenant/church is unknown, 403 when the user may not touch it."""
    tenant = await tenant_repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    if tenant.name == CHWZ_ORG_TENANT_NAME:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    church = await church_repo.get_church_by_id(tenant_id)
    if not church:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Church {tenant_id} not found",
        )

    if not await permission_service.resolve(current_user, permission, ("church", church.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


class TenantAccessChecker:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        permission_service: PermissionService,
        church_repo: ChurchRepository,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._permission_service = permission_service
        self._church_repo = church_repo

    async def verify(
        self,
        tenant_id: str,
        current_user: User,
        *,
        permission: str = "church.edit",
    ) -> None:
        await verify_tenant_access(
            tenant_id,
            current_user,
            self._tenant_repo,
            self._permission_service,
            self._church_repo,
            permission=permission,
        )


def get_tenant_access_checker(
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
) -> TenantAccessChecker:
    return TenantAccessChecker(tenant_repo, permission_service, church_repo)
