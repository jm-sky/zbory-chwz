"""API router for managing congregation share links."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import AdminOrOwnerUser, CurrentUser
from app.modules.sharing.schemas import (
    ShareLinkCreateRequest,
    ShareLinkListResponse,
    ShareLinkResponse,
)
from app.modules.sharing.service import ShareLinkService, get_share_link_service
from app.modules.tenants.access import verify_tenant_access
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository

router = APIRouter(prefix="/congregations", tags=["Sharing"])
# All-congregations share links: admin/owner only, not scoped to a single tenant.
global_router = APIRouter(prefix="/share-links", tags=["Sharing"])


@router.post(
    "/{tenant_id}/share-links",
    status_code=status.HTTP_201_CREATED,
    response_model=ShareLinkResponse,
)
@rate_limit("10/hour")
async def create_share_link(
    request: Request,
    tenant_id: str,
    payload: ShareLinkCreateRequest,
    current_user: CurrentUser,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> ShareLinkResponse:
    """Create an anonymous, time-limited share link for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    share_link = await service.create_share_link(
        tenant_id=tenant_id,
        created_by_user_id=current_user.id,
        visibility_level=payload.visibility_level,
        expires_in_days=payload.expires_in_days,
        label=payload.label,
    )
    return ShareLinkResponse.model_validate(share_link, from_attributes=True)


@router.get("/{tenant_id}/share-links", response_model=ShareLinkListResponse)
async def list_share_links(
    tenant_id: str,
    current_user: CurrentUser,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> ShareLinkListResponse:
    """List active (non-revoked) share links for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    links = await service.repository.list_active_for_tenant(tenant_id)
    return ShareLinkListResponse(
        links=[ShareLinkResponse.model_validate(link, from_attributes=True) for link in links],
    )


@router.delete("/{tenant_id}/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    tenant_id: str,
    link_id: str,
    current_user: CurrentUser,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> None:
    """Revoke a share link, taking effect immediately."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    share_link = await service.repository.get_by_id(link_id, tenant_id)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Share link {link_id} not found",
        )

    await service.repository.revoke(share_link)


@global_router.post("", status_code=status.HTTP_201_CREATED, response_model=ShareLinkResponse)
@rate_limit("10/hour")
async def create_global_share_link(
    request: Request,
    payload: ShareLinkCreateRequest,
    current_user: AdminOrOwnerUser,
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> ShareLinkResponse:
    """Create an anonymous, time-limited share link for every congregation the creator can see."""
    share_link = await service.create_share_link(
        tenant_id=None,
        created_by_user_id=current_user.id,
        visibility_level=payload.visibility_level,
        expires_in_days=payload.expires_in_days,
        label=payload.label,
    )
    return ShareLinkResponse.model_validate(share_link, from_attributes=True)


@global_router.get("", response_model=ShareLinkListResponse)
async def list_global_share_links(
    current_user: AdminOrOwnerUser,
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> ShareLinkListResponse:
    """List the current admin/owner's active all-congregations share links."""
    links = await service.repository.list_active_for_user(current_user.id)
    return ShareLinkListResponse(
        links=[ShareLinkResponse.model_validate(link, from_attributes=True) for link in links],
    )


@global_router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_global_share_link(
    link_id: str,
    current_user: AdminOrOwnerUser,
    service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> None:
    """Revoke an all-congregations share link, taking effect immediately."""
    share_link = await service.repository.get_by_id_for_user(link_id, current_user.id)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Share link {link_id} not found",
        )

    await service.repository.revoke(share_link)
