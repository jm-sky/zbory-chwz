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

PUBLIC_ADDRESS_STATUSES = ("published", "published_unverified")
MAX_PUBLIC_SERVICE_TIMES = 3


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

    Returns congregations with status 'published' or 'published_unverified', each
    followed by its publicly visible branches (placówki). Uses address.status for
    filtering (address status takes precedence over tenant status).

    A congregation's church row shares its id with the tenant (see
    `churches.provisioning`), so tenant ids double as church ids here.
    """
    all_tenants = await repo.list_all()
    addresses = await congregation_repo.get_addresses_by_status(PUBLIC_ADDRESS_STATUSES)

    published = [tenant for tenant in all_tenants if tenant.id in addresses]
    tenant_ids = [tenant.id for tenant in published]

    service_times_by_tenant = await congregation_repo.get_service_times_for_tenants(
        tenant_ids
    )
    assignments_by_church = await church_repo.list_public_card_assignments_for_churches(
        tenant_ids
    )
    branches_by_church = await church_repo.list_public_branches_for_churches(tenant_ids)

    congregations: list[PublicCongregationResponse] = []
    for tenant in published:
        address = addresses[tenant.id]
        service_times = [
            {"day": st.day, "time": st.time}
            for st in service_times_by_tenant.get(tenant.id, [])[
                :MAX_PUBLIC_SERVICE_TIMES
            ]
        ]

        card_contacts = [
            PublicCardContact(
                **church_repo.to_public_card_contact(
                    assignment,
                    is_authenticated=False,
                    has_pastoral_access=False,
                )
            )
            for assignment in assignments_by_church.get(tenant.id, [])
        ]
        primary_contact = card_contacts[0] if card_contacts else None

        congregations.append(
            PublicCongregationResponse(
                id=tenant.id,
                name=tenant.name,
                description=tenant.description,
                status=address.status,
                createdAt=tenant.created_at,
                type="church",
                city=address.city,
                street=address.street,
                postal_code=address.postal_code,
                province=address.province,
                country=address.country,
                service_times=service_times,
                card_contacts=card_contacts,
                contact_name=primary_contact.name if primary_contact else None,
                contact_title=primary_contact.title if primary_contact else None,
                contact_phone=primary_contact.phone if primary_contact else None,
                contact_email=primary_contact.email if primary_contact else None,
            )
        )

        # Branches have no address of their own; they inherit the congregation's
        # location so they can be filtered by country and province alongside it.
        for branch in branches_by_church.get(tenant.id, []):
            congregations.append(
                PublicCongregationResponse(
                    id=branch.id,
                    name=branch.name,
                    status=address.status,
                    createdAt=branch.created_at,
                    type="branch",
                    parent_id=tenant.id,
                    parent_name=tenant.name,
                    city=address.city,
                    province=address.province,
                    country=address.country,
                )
            )

    return PublicCongregationListResponse(congregations=congregations)
