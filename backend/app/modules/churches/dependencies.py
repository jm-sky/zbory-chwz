"""FastAPI dependencies for ACL permission checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.churches.db_models import ChurchDB
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.seed_data import CHWZ_ORG_TENANT_NAME
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository


async def _church_id_from_tenant(
    tenant_id: str,
    tenant_repo: TenantRepository,
    church_repo: ChurchRepository,
) -> str:
    tenant = await tenant_repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found")
    if tenant.name == CHWZ_ORG_TENANT_NAME:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    church = await church_repo.get_church_by_id(tenant_id)
    if not church:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Church {tenant_id} not found")
    return church.id


def RequirePermission(
    permission: str,
    *,
    param: str = "church_id",
    scope_type: str = "church",
) -> Callable[..., User]:
    async def _dependency(
        request: Request,
        current_user: CurrentUser,
        permission_service: Annotated[PermissionService, Depends(get_permission_service)],
        church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
        tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    ) -> User:
        raw_id = request.path_params.get(param)
        if not raw_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing path parameter {param}")

        if scope_type == "church" and param == "tenant_id":
            church_id = await _church_id_from_tenant(raw_id, tenant_repo, church_repo)
            scope: tuple[str, str] = ("church", church_id)
        elif scope_type == "church":
            church = await church_repo.get_church_by_id(raw_id)
            if not church:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Church not found")
            scope = ("church", church.id)
        else:
            scope = (scope_type, raw_id)

        if not await permission_service.resolve(current_user, permission, scope):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return current_user

    return _dependency
