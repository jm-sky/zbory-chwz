"""API router for tenant management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import CurrentUser, OptionalCurrentUser
from app.modules.churches.acl_service import AclService, get_acl_service
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.visibility import VisibilityService
from app.modules.congregations.db_models import decode_coordinate
from app.modules.congregations.repositories import (
    CongregationRepository,
    get_congregation_repository,
)
from app.modules.sharing.service import ShareLinkService, get_share_link_service
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository
from app.modules.tenants.schemas import (
    CongregationBranchSummary,
    CongregationDetailResponse,
    PublicCardContact,
    PublicCongregationListResponse,
    PublicCongregationResponse,
    ShareResolveResponse,
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])
# Public congregations router (for listing published congregations)
public_congregations_router = APIRouter(prefix="/congregations", tags=["Congregations"])
# Anonymous share-link resolution (no auth, no tenant membership)
public_share_router = APIRouter(prefix="/share", tags=["Sharing"])

PUBLIC_ADDRESS_STATUSES = ("published", "published_unverified")
MAX_PUBLIC_SERVICE_TIMES = 3


async def _build_congregation_detail(
    tenant: TenantDB,
    *,
    is_authenticated: bool,
    has_pastoral_access: bool,
    is_member: bool,
    membership_role: str | None,
    congregation_repo: CongregationRepository,
    church_repo: ChurchRepository,
) -> CongregationDetailResponse:
    """Build the filtered congregation detail shared by the authenticated/public
    detail endpoint and the anonymous share-link viewer."""
    address = await congregation_repo.get_address_by_tenant_id(tenant.id)
    status_value = address.status if address else (tenant.status or "draft")
    if status_value not in PUBLIC_ADDRESS_STATUSES and not is_member:
        raise HTTPException(status_code=404, detail=f"Congregation {tenant.id} not found")

    service_times = await congregation_repo.get_service_times_by_tenant_id(tenant.id)

    assignments = await church_repo.list_service_assignments("church", tenant.id)
    visible_contacts, hidden_contacts = church_repo.profile_contacts_for_viewer(
        assignments,
        is_authenticated=is_authenticated,
        has_pastoral_access=has_pastoral_access,
        can_manage=is_member,
    )
    card_contacts = [PublicCardContact(**contact) for contact in visible_contacts]
    hidden_profile_contacts = [PublicCardContact(**contact) for contact in hidden_contacts] if is_member else []

    branches = await church_repo.list_branches(tenant.id)
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
        website=address.website if address else None,
        email=address.email if address else None,
        iban=address.iban if address else None,
        latitude=decode_coordinate(address.latitude) if address else None,
        longitude=decode_coordinate(address.longitude) if address else None,
        service_times=[{"day": service_time.day, "time": service_time.time, "description": service_time.description} for service_time in service_times],
        card_contacts=card_contacts,
        hidden_contacts=hidden_profile_contacts,
        branches=[CongregationBranchSummary(id=branch.id, name=branch.name) for branch in visible_branches],
        role=membership_role,
        canManage=is_member,
    )


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


async def _build_published_congregations(
    repo: TenantRepository,
    congregation_repo: CongregationRepository,
    church_repo: ChurchRepository,
    *,
    is_authenticated: bool,
    has_pastoral_access: bool = False,
) -> list[PublicCongregationResponse]:
    """Build the published-congregations-with-branches list shared by the public
    detailed listing and the anonymous all-congregations share-link viewer."""
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
        service_times = [{"day": st.day, "time": st.time, "description": st.description} for st in service_times_by_tenant.get(tenant.id, [])[:MAX_PUBLIC_SERVICE_TIMES]]

        card_contacts = [
            PublicCardContact(
                **church_repo.to_public_card_contact(
                    assignment,
                    is_authenticated=is_authenticated,
                    has_pastoral_access=has_pastoral_access,
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
                website=address.website,
                email=address.email,
                iban=address.iban,
                latitude=decode_coordinate(address.latitude),
                longitude=decode_coordinate(address.longitude),
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
                    latitude=decode_coordinate(address.latitude),
                    longitude=decode_coordinate(address.longitude),
                )
            )

    return congregations


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
    congregations = await _build_published_congregations(repo, congregation_repo, church_repo, is_authenticated=False)
    all_tenants = await repo.list_all()
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
                        latitude=decode_coordinate(address.latitude) if address else None,
                        longitude=decode_coordinate(address.longitude) if address else None,
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

    Profile contacts are filtered by profile_visibility and the viewer's
    permission level. Hidden contacts are returned separately for editors
    (canManage). Phone and email are filtered per field. Members and
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

    return await _build_congregation_detail(
        tenant,
        is_authenticated=is_authenticated,
        has_pastoral_access=has_pastoral_access,
        is_member=is_member,
        membership_role=membership_role,
        congregation_repo=congregation_repo,
        church_repo=church_repo,
    )


@public_share_router.get("/{token}", response_model=ShareResolveResponse)
@rate_limit("30/minute")
async def get_shared_congregation(
    request: Request,
    token: str,
    repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    congregation_repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    share_link_service: Annotated[ShareLinkService, Depends(get_share_link_service)],
) -> ShareResolveResponse:
    """Resolve an anonymous share link.

    A tenant-scoped link resolves to that congregation's filtered detail view.
    An all-congregations link (created by an admin/owner, no single tenant)
    resolves to the same published-congregations list as the public directory.

    The granted visibility level (public/authenticated/pastors) is the read-only
    ceiling for what the anonymous visitor sees: it only widens which contact
    fields are revealed. They never get membership or canManage, regardless of
    who created the link or which level was granted.
    """
    share_link, _reason = await share_link_service.resolve_token(token)
    if share_link is None:
        # Collapsed reason (not_found/expired/revoked) on purpose: distinguishing
        # them helps an attacker probe tokens more than it helps a real visitor.
        raise HTTPException(status_code=404, detail="This link is no longer valid")

    is_authenticated = share_link.visibility_level in ("authenticated", "pastors")
    has_pastoral_access = share_link.visibility_level == "pastors"

    if share_link.tenant_id is None:
        congregations = await _build_published_congregations(
            repo,
            congregation_repo,
            church_repo,
            is_authenticated=is_authenticated,
            has_pastoral_access=has_pastoral_access,
        )
        return ShareResolveResponse(kind="congregations", congregations=congregations)

    tenant = await repo.get_tenant(share_link.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="This link is no longer valid")

    congregation = await _build_congregation_detail(
        tenant,
        is_authenticated=is_authenticated,
        has_pastoral_access=has_pastoral_access,
        is_member=False,
        membership_role=None,
        congregation_repo=congregation_repo,
        church_repo=church_repo,
    )
    return ShareResolveResponse(kind="congregation", congregation=congregation)
