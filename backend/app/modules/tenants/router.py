"""API router for tenant management."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.congregations.repositories import (
    CongregationRepository,
    get_congregation_repository,
)
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository
from app.modules.tenants.schemas import (
    PublicCardContact,
    PublicCongregationListResponse,
    PublicCongregationResponse,
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
)


router = APIRouter(prefix="/tenants", tags=["Tenants"])
# Public congregations router (for listing published congregations)
public_congregations_router = APIRouter(prefix="/congregations", tags=["Congregations"])


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    current_user: CurrentUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantListResponse:
    items = await repo.list_for_user(current_user.id)
    tenants = [
        TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=tenant.status,
            role=membership.role,
            createdAt=tenant.created_at,
        )
        for tenant, membership in items
    ]
    return TenantListResponse(tenants=tenants)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(
    payload: TenantCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantResponse:
    tenant, membership = await repo.create_tenant(
        name=payload.name,
        description=payload.description,
        owner_user_id=current_user.id,
    )
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        description=tenant.description,
        role=membership.role,
        createdAt=tenant.created_at,
    )


@public_congregations_router.get("", response_model=TenantListResponse)
async def list_congregations(
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantListResponse:
    """Public endpoint to list only published congregations (tenants).

    Note: Currently uses tenant.status for filtering. In the future, this should
    filter by congregation/address status when that module is implemented.
    """
    tenants = await repo.list_published()
    congregations = [
        TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            role="",  # Public endpoint doesn't include role
            createdAt=tenant.created_at,
        )
        for tenant in tenants
    ]
    return TenantListResponse(tenants=congregations)


@public_congregations_router.get(
    "/detailed", response_model=PublicCongregationListResponse
)
async def list_congregations_detailed(
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    congregation_repo: Annotated[
        CongregationRepository, Depends(get_congregation_repository)
    ],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
) -> PublicCongregationListResponse:
    """Public endpoint to list published congregations with detailed info (address, service times, contact).

    Returns congregations with status 'published' or 'published_unverified'.
    Uses address.status for filtering (address status takes precedence over tenant status).
    """
    # Get all tenants (we'll filter by address status)
    all_tenants = await repo.list_all()
    congregations = []

    for tenant in all_tenants:
        # Get address
        address = await congregation_repo.get_address_by_tenant_id(tenant.id)

        # Filter by address status: only 'published' or 'published_unverified'
        if address and address.status in ("published", "published_unverified"):
            # Get service times (limit to first 3)
            service_times_db = await congregation_repo.get_service_times_by_tenant_id(
                tenant.id
            )
            service_times = [
                {"day": st.day, "time": st.time}
                for st in service_times_db[:3]  # Limit to first 3
            ]

            assignments = await church_repo.list_public_card_assignments(tenant.id)
            card_contacts = [
                PublicCardContact(
                    **church_repo.to_public_card_contact(
                        assignment,
                        is_authenticated=False,
                        has_pastoral_access=False,
                    )
                )
                for assignment in assignments
            ]
            primary_contact = card_contacts[0] if card_contacts else None

            congregations.append(
                PublicCongregationResponse(
                    id=tenant.id,
                    name=tenant.name,
                    description=tenant.description,
                    status=address.status,
                    createdAt=tenant.created_at,
                    city=address.city if address else None,
                    street=address.street if address else None,
                    postal_code=address.postal_code if address else None,
                    service_times=service_times,
                    card_contacts=card_contacts,
                    contact_name=primary_contact.name if primary_contact else None,
                    contact_title=primary_contact.title if primary_contact else None,
                    contact_phone=primary_contact.phone if primary_contact else None,
                    contact_email=primary_contact.email if primary_contact else None,
                )
            )

    return PublicCongregationListResponse(congregations=congregations)
