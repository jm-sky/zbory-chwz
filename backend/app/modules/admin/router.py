"""FastAPI router for admin endpoints.

This module provides admin-only endpoints for managing users.
All endpoints require admin authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.repositories import (
    UserRepository as AuthUserRepository,
    get_user_repository as get_auth_user_repository,
)
from app.modules.auth.dependencies import AdminOrOwnerUser, AdminUser
from app.modules.users.repositories import UserRepository, get_user_repository
from app.modules.users.schemas import UserUpdate

from .repository import AdminRepository
from .schemas import AdminUserResponse
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_repository(db: AsyncSession = Depends(get_db)) -> AdminRepository:
    """Dependency to get admin repository instance."""
    return AdminRepository(db)


def get_admin_service(
    repository: AdminRepository = Depends(get_admin_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    auth_user_repository: AuthUserRepository = Depends(get_auth_user_repository),
) -> AdminService:
    """Dependency to get admin service instance."""
    return AdminService(repository, user_repository, auth_user_repository)


# Users endpoints
@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="Get all users (admin only)",
    description="Get list of all users with pagination",
)
async def get_all_users(
    _: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
) -> list[AdminUserResponse]:
    """Get all users (admin only)."""
    return await service.get_all_users(skip=skip, limit=limit)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get user by ID (admin only)",
    description="Get a specific user by their ID",
)
async def get_user_by_id(
    user_id: str,
    _: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> AdminUserResponse:
    """Get user by ID (admin only)."""
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return user


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user (admin only)",
    description="Update user information",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> AdminUserResponse:
    """Update user (admin or owner only)."""
    user = await service.update_user(user_id, user_data, current_user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (admin only)",
    description="Delete a user (soft delete - sets isActive to false)",
)
async def delete_user(
    user_id: str,
    current_user: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> None:
    """Delete user (admin or owner only)."""
    success = await service.delete_user(user_id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )


# Tenants/Congregations endpoints
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository
from app.modules.tenants.schemas import (
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
    TenantUpdateRequest,
    TenantMembershipResponse,
    TenantMembershipCreateRequest,
    TenantMembershipUpdateRequest,
)
from app.modules.tenants.db_models import TenantMembershipDB
from app.modules.users.repositories import UserRepository


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    summary="Get all tenants (admin only)",
    description="Get list of all tenants (congregations)",
)
async def get_all_tenants(
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantListResponse:
    """Get all tenants (admin only)."""
    tenants = await repo.list_all()
    return TenantListResponse(
        tenants=[
            TenantResponse(
                id=tenant.id,
                name=tenant.name,
                description=tenant.description,
                status=tenant.status,
                role="",  # Admin view doesn't include role
                createdAt=tenant.created_at,
            )
            for tenant in tenants
        ]
    )


@router.post(
    "/tenants",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantResponse,
    summary="Create tenant (admin only)",
    description="Create a new tenant (congregation)",
)
async def create_tenant_admin(
    payload: TenantCreateRequest,
    current_user: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantResponse:
    """Create tenant (admin only)."""
    tenant, membership = await repo.create_tenant(
        name=payload.name,
        description=payload.description,
        owner_user_id=current_user.id,
        status=payload.status or "draft",
    )
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        description=tenant.description,
        status=tenant.status,
        role=membership.role,
        createdAt=tenant.created_at,
    )


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant (admin only)",
    description="Update tenant information and status",
)
async def update_tenant_admin(
    tenant_id: str,
    payload: TenantUpdateRequest,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantResponse:
    """Update tenant (admin only)."""
    tenant = await repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found"
        )
    
    # Update fields
    if payload.name is not None:
        tenant.name = payload.name
    if payload.description is not None:
        tenant.description = payload.description
    if payload.status is not None:
        tenant.status = payload.status
    
    await repo.db.commit()
    await repo.db.refresh(tenant)
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        description=tenant.description,
        status=tenant.status,
        role="",
        createdAt=tenant.created_at,
    )


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant (admin only)",
    description="Delete a tenant (congregation)",
)
async def delete_tenant_admin(
    tenant_id: str,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    """Delete tenant (admin only)."""
    tenant = await repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found"
        )
    
    await repo.db.delete(tenant)
    await repo.db.commit()


# Tenant Memberships endpoints
@router.get(
    "/tenants/{tenant_id}/memberships",
    response_model=list[TenantMembershipResponse],
    summary="Get tenant memberships (admin only)",
    description="Get all memberships for a tenant",
)
async def get_tenant_memberships(
    tenant_id: str,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[TenantMembershipResponse]:
    """Get tenant memberships (admin only)."""
    tenant = await repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found"
        )
    
    from sqlalchemy import select
    stmt = select(TenantMembershipDB).where(
        TenantMembershipDB.tenant_id == tenant_id
    ).order_by(TenantMembershipDB.created_at)
    result = await repo.db.execute(stmt)
    memberships = result.scalars().all()
    
    membership_responses = []
    for membership in memberships:
        user = await user_repo.get_user_by_id(membership.user_id)
        membership_responses.append(
            TenantMembershipResponse(
                tenant_id=membership.tenant_id,
                user_id=membership.user_id,
                user_name=user.name if user else None,
                user_email=user.email if user else None,
                role=membership.role,
                createdAt=membership.created_at,
            )
        )
    
    return membership_responses


@router.post(
    "/tenants/{tenant_id}/memberships",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantMembershipResponse,
    summary="Add tenant membership (admin only)",
    description="Add a user to a tenant with a role",
)
async def add_tenant_membership(
    tenant_id: str,
    payload: TenantMembershipCreateRequest,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TenantMembershipResponse:
    """Add tenant membership (admin only)."""
    tenant = await repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found"
        )
    
    user = await user_repo.get_user_by_id(payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {payload.user_id} not found"
        )
    
    membership = await repo.add_member(
        tenant_id=tenant_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    
    return TenantMembershipResponse(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        user_name=user.name,
        user_email=user.email,
        role=membership.role,
        createdAt=membership.created_at,
    )


@router.patch(
    "/tenants/{tenant_id}/memberships/{user_id}",
    response_model=TenantMembershipResponse,
    summary="Update tenant membership (admin only)",
    description="Update a user's role in a tenant",
)
async def update_tenant_membership(
    tenant_id: str,
    user_id: str,
    payload: TenantMembershipUpdateRequest,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TenantMembershipResponse:
    """Update tenant membership (admin only)."""
    from sqlalchemy import select
    stmt = select(TenantMembershipDB).where(
        TenantMembershipDB.tenant_id == tenant_id,
        TenantMembershipDB.user_id == user_id,
    )
    result = await repo.db.execute(stmt)
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Membership not found for tenant {tenant_id} and user {user_id}",
        )
    
    membership.role = payload.role
    await repo.db.commit()
    await repo.db.refresh(membership)
    
    user = await user_repo.get_user_by_id(user_id)
    return TenantMembershipResponse(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        role=membership.role,
        createdAt=membership.created_at,
    )


@router.delete(
    "/tenants/{tenant_id}/memberships/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tenant membership (admin only)",
    description="Remove a user from a tenant",
)
async def remove_tenant_membership(
    tenant_id: str,
    user_id: str,
    _: AdminOrOwnerUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    """Remove tenant membership (admin only)."""
    from sqlalchemy import select
    stmt = select(TenantMembershipDB).where(
        TenantMembershipDB.tenant_id == tenant_id,
        TenantMembershipDB.user_id == user_id,
    )
    result = await repo.db.execute(stmt)
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Membership not found for tenant {tenant_id} and user {user_id}",
        )
    
    await repo.db.delete(membership)
    await repo.db.commit()
