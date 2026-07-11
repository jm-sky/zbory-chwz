"""API router for tenant management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import CurrentUser, OptionalCurrentUser
from app.modules.churches.acl_service import AclService, get_acl_service
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.visibility import VisibilityService
from app.modules.congregations.repositories import (
    CongregationRepository,
    get_congregation_repository,
)
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository
from app.modules.tenants.schemas import (
    CongregationBranchSummary,
    CongregationDetailResponse,
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


@public_congregations_router.get("/detailed", response_model=PublicCongregationListResponse)
async def list_congregations_detailed(
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    congregation_repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    current_user: OptionalCurrentUser,
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

    service_times_by_tenant = await congregation_repo.get_service_times_for_tenants(tenant_ids)
    assignments_by_church = await church_repo.list_public_card_assignments_for_churches(tenant_ids)
    branches_by_church = await church_repo.list_public_branches_for_churches(tenant_ids)

    congregations: list[PublicCongregationResponse] = []
    for tenant in published:
        address = addresses[tenant.id]
        service_times = [{"day": st.day, "time": st.time} for st in service_times_by_tenant.get(tenant.id, [])[:MAX_PUBLIC_SERVICE_TIMES]]

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

    published_ids = {congregation.id for congregation in congregations}

    if current_user is not None:
        if current_user.isAdmin or current_user.isOwner:
            draft_tenants = [tenant for tenant in all_tenants if tenant.id not in published_ids]
        else:
            draft_tenants = [tenant for tenant, _membership in await repo.list_for_user(current_user.id) if tenant.id not in published_ids]

        if draft_tenants:
            draft_addresses = await congregation_repo.get_addresses_by_status(("draft",))
            for tenant in draft_tenants:
                address = draft_addresses.get(tenant.id)
                congregations.append(
                    PublicCongregationResponse(
                        id=tenant.id,
                        name=tenant.name,
                        description=tenant.description,
                        status="draft",
                        createdAt=tenant.created_at,
                        type="church",
                        city=address.city if address else None,
                        street=address.street if address else None,
                        postal_code=address.postal_code if address else None,
                        province=address.province if address else None,
                        country=address.country if address else None,
                    )
                )

    return PublicCongregationListResponse(congregations=congregations)


@public_congregations_router.get("/{tenant_id}/detail", response_model=CongregationDetailResponse)
async def get_congregation_detail(
    tenant_id: str,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    congregation_repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    acl_service: Annotated[AclService, Depends(get_acl_service)],
    current_user: OptionalCurrentUser,
) -> CongregationDetailResponse:
    """Public endpoint for a single congregation.

    Lists every service assignment on the detail page; card_visibility only
    affects the congregation list card, not this view. Phone and email are
    still filtered per field by the viewer's permission level. Members and
    global admins/owners also see unpublished drafts.
    """
    tenant = await repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Congregation {tenant_id} not found")

    is_authenticated = current_user is not None
    is_admin = current_user is not None and (current_user.isAdmin or current_user.isOwner)

    membership_role: str | None = None
    if current_user is not None and not is_admin:
        memberships = await repo.list_for_user(current_user.id)
        membership_role = next(
            (membership.role for membership_tenant, membership in memberships if membership_tenant.id == tenant_id),
            None,
        )
    is_member = is_admin or membership_role is not None

    has_pastoral_access = await acl_service.has_pastoral_access(current_user.id, tenant_id) if current_user is not None else False

    address = await congregation_repo.get_address_by_tenant_id(tenant_id)
    status_value = address.status if address else (tenant.status or "draft")
    if status_value not in PUBLIC_ADDRESS_STATUSES and not is_member:
        raise HTTPException(status_code=404, detail=f"Congregation {tenant_id} not found")

    service_times = await congregation_repo.get_service_times_by_tenant_id(tenant_id)

    assignments = await church_repo.list_service_assignments("church", tenant_id)
    card_contacts = [
        PublicCardContact(
            **church_repo.to_public_card_contact(
                assignment,
                is_authenticated=is_authenticated,
                has_pastoral_access=has_pastoral_access,
            )
        )
        for assignment in assignments
    ]

    branches = await church_repo.list_branches(tenant_id)
    visible_branches = [
        branch
        for branch in branches
        if (is_member and branch.visibility != "hidden")
        or VisibilityService.can_view(
            branch.visibility,
            is_authenticated=is_authenticated,
            has_pastoral_access=has_pastoral_access,
        )
    ]

    return CongregationDetailResponse(
        id=tenant.id,
        name=tenant.name,
        description=tenant.description,
        status=status_value,
        createdAt=tenant.created_at,
        city=address.city if address else None,
        street=address.street if address else None,
        postal_code=address.postal_code if address else None,
        province=address.province if address else None,
        country=address.country if address else None,
        service_times=[{"day": service_time.day, "time": service_time.time} for service_time in service_times],
        card_contacts=card_contacts,
        branches=[CongregationBranchSummary(id=branch.id, name=branch.name) for branch in visible_branches],
        role=membership_role,
        canManage=is_member,
    )
