"""API router for congregation management (addresses, service times)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.limiter import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.churches.acl_service import AclService, get_acl_service
from app.modules.congregations.db_models import CongregationAddressDB, decode_coordinate
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB
from app.modules.congregations.field_diff import (
    ADDRESS_FIELDS,
    FIELD_LABELS,
    MANUAL_ONLY_FIELD_LABELS,
)
from app.modules.congregations.geo import is_valid_province
from app.modules.congregations.geocoding import geocode_address
from app.modules.congregations.repositories import (
    CongregationRepository,
    get_congregation_repository,
)
from app.modules.congregations.schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
    ChangeLogBatch,
    ChangeLogFieldChange,
    ChangeLogResponse,
    CongregationFullResponse,
    CongregationUpdateRequest,
    CongregationUpdateResponse,
    GeocodeRequest,
    GeocodeResponse,
    ServiceTimeCreateRequest,
    ServiceTimeResponse,
    ServiceTimeUpdateRequest,
)
from app.modules.tenants.access import TenantAccessChecker, get_tenant_access_checker
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository

router = APIRouter(prefix="/congregations", tags=["Congregations"])


async def _verify_change_log_access(
    tenant_id: str,
    current_user: User,
    access: TenantAccessChecker,
    acl_service: AclService,
) -> None:
    """Admins, tenant members (the classic access route pastors already use
    to manage their own congregation), and anyone with pastoral ACL access
    to this church (covers regional/national bishops with no direct tenant
    membership) can see the change history. Everyone else gets 403."""
    try:
        await access.verify(tenant_id, current_user)
        return
    except HTTPException as exc:
        if exc.status_code != status.HTTP_403_FORBIDDEN:
            raise

    if await acl_service.has_pastoral_access(current_user, tenant_id):
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _group_change_log_by_batch(
    rows: list[CongregationChangeLogDB],
) -> list[ChangeLogBatch]:
    """Group flat change-log rows (as returned by the repo, batch-ordered) into batches."""
    batches: dict[str, list[CongregationChangeLogDB]] = {}
    order: list[str] = []
    for row in rows:
        if row.batch_id not in batches:
            batches[row.batch_id] = []
            order.append(row.batch_id)
        batches[row.batch_id].append(row)

    return [
        ChangeLogBatch(
            batch_id=batch_id,
            source=batches[batch_id][0].source,  # type: ignore[arg-type]
            actor_label=batches[batch_id][0].actor_label,
            created_at=max(row.created_at for row in batches[batch_id]),
            changes=[
                ChangeLogFieldChange(
                    id=row.id,
                    section=row.section,  # type: ignore[arg-type]
                    field=row.field,
                    field_label=FIELD_LABELS.get(row.field) or MANUAL_ONLY_FIELD_LABELS.get(row.field, row.field),
                    old_value=row.old_value,
                    new_value=row.new_value,
                )
                for row in batches[batch_id]
            ],
        )
        for batch_id in order
    ]


def _address_snapshot(address: CongregationAddressDB | None) -> dict[str, str | None]:
    if address is None:
        return dict.fromkeys(ADDRESS_FIELDS)
    return {field: getattr(address, field) for field in ADDRESS_FIELDS}


async def _log_address_changes(
    repo: CongregationRepository,
    tenant_id: str,
    current_user: User,
    before: dict[str, str | None],
    after: dict[str, str | None],
) -> None:
    changes = {field: (before[field], after[field]) for field in ADDRESS_FIELDS if before[field] != after[field]}
    await repo.log_changes(
        tenant_id,
        section="address",
        changes=changes,
        source="admin_manual",
        actor_label=current_user.name,
        actor_user_id=current_user.id,
    )


@router.patch(
    "/{tenant_id}",
    response_model=CongregationUpdateResponse,
    summary="Update congregation basic info",
    description="Update name/description/status; open to tenant members (not just admins).",
)
async def update_congregation(
    tenant_id: str,
    payload: CongregationUpdateRequest,
    current_user: CurrentUser,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> CongregationUpdateResponse:
    """Update congregation (any tenant member or admin/owner)."""
    await access.verify(tenant_id, current_user)

    tenant = await tenant_repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    if payload.name is not None:
        tenant.name = payload.name
    if payload.description is not None:
        tenant.description = payload.description
    if payload.status is not None:
        tenant.status = payload.status

    await tenant_repo.db.commit()
    await tenant_repo.db.refresh(tenant)

    role: str | None = None
    if not (current_user.isAdmin or current_user.isOwner):
        memberships = await tenant_repo.list_for_user(current_user.id)
        role = next((membership.role for membership_tenant, membership in memberships if membership_tenant.id == tenant_id), None)

    return CongregationUpdateResponse(
        id=tenant.id,
        name=tenant.name,
        description=tenant.description,
        status=tenant.status,
        role=role,
        createdAt=tenant.created_at,
    )


# Address endpoints
@router.get("/{tenant_id}/address", response_model=AddressResponse)
async def get_address(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> AddressResponse:
    """Get address for a congregation."""
    await access.verify(tenant_id, current_user)

    address = await repo.get_address_by_tenant_id(tenant_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address not found for tenant {tenant_id}",
        )

    return AddressResponse(
        id=address.id,
        tenant_id=address.tenant_id,
        street=address.street,
        city=address.city,
        postal_code=address.postal_code,
        province=address.province,
        country=address.country,
        website=address.website,
        email=address.email,
        iban=address.iban,
        latitude=decode_coordinate(address.latitude),
        longitude=decode_coordinate(address.longitude),
        geocode_status=address.geocode_status,
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
        last_updated_at=address.last_updated_at,
        last_updated_label=address.last_updated_label,
    )


@router.post(
    "/{tenant_id}/address",
    status_code=status.HTTP_201_CREATED,
    response_model=AddressResponse,
)
async def create_address(
    tenant_id: str,
    payload: AddressCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> AddressResponse:
    """Create or update address for a congregation."""
    await access.verify(tenant_id, current_user)

    before = _address_snapshot(await repo.get_address_by_tenant_id(tenant_id))

    address = await repo.create_or_update_address(
        tenant_id=tenant_id,
        street=payload.street,
        city=payload.city,
        postal_code=payload.postal_code,
        province=payload.province,
        country=payload.country,
        website=payload.website,
        email=payload.email,
        iban=payload.iban,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status=payload.status,
    )

    await _log_address_changes(repo, tenant_id, current_user, before, _address_snapshot(address))

    return AddressResponse(
        id=address.id,
        tenant_id=address.tenant_id,
        street=address.street,
        city=address.city,
        postal_code=address.postal_code,
        province=address.province,
        country=address.country,
        website=address.website,
        email=address.email,
        iban=address.iban,
        latitude=decode_coordinate(address.latitude),
        longitude=decode_coordinate(address.longitude),
        geocode_status=address.geocode_status,
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
        last_updated_at=address.last_updated_at,
        last_updated_label=address.last_updated_label,
    )


@router.patch("/{tenant_id}/address", response_model=AddressResponse)
async def update_address(
    tenant_id: str,
    payload: AddressUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> AddressResponse:
    """Update address for a congregation."""
    await access.verify(tenant_id, current_user)

    address = await repo.get_address_by_tenant_id(tenant_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address not found for tenant {tenant_id}",
        )

    before = _address_snapshot(address)

    # Update fields
    if payload.street is not None:
        address.street = payload.street
    if payload.city is not None:
        address.city = payload.city
    if payload.postal_code is not None:
        address.postal_code = payload.postal_code
    if payload.province is not None:
        address.province = payload.province
    if payload.country is not None:
        address.country = payload.country
    if payload.website is not None:
        address.website = payload.website
    if payload.email is not None:
        address.email = payload.email
    if payload.iban is not None:
        address.iban = payload.iban
    if payload.latitude is not None:
        address.latitude = str(payload.latitude)
        address.geocode_status = "manual"
    if payload.longitude is not None:
        address.longitude = str(payload.longitude)
        address.geocode_status = "manual"
    if payload.status is not None:
        address.status = payload.status

    # A partial patch can change either side of the pair, so validate the merge.
    if not is_valid_province(address.country, address.province):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{address.province!r} is not a province of {address.country}",
        )

    address.updated_at = datetime.now(UTC)

    await repo.db.commit()
    await repo.db.refresh(address)

    await _log_address_changes(repo, tenant_id, current_user, before, _address_snapshot(address))

    return AddressResponse(
        id=address.id,
        tenant_id=address.tenant_id,
        street=address.street,
        city=address.city,
        postal_code=address.postal_code,
        province=address.province,
        country=address.country,
        website=address.website,
        email=address.email,
        iban=address.iban,
        latitude=decode_coordinate(address.latitude),
        longitude=decode_coordinate(address.longitude),
        geocode_status=address.geocode_status,
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
        last_updated_at=address.last_updated_at,
        last_updated_label=address.last_updated_label,
    )


@router.post("/{tenant_id}/address/geocode", response_model=GeocodeResponse)
@rate_limit("10/minute")
async def geocode_congregation_address(
    tenant_id: str,
    payload: GeocodeRequest,
    current_user: CurrentUser,
    request: Request,
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> GeocodeResponse:
    """Preview coordinates for an address without saving them.

    Does not write to the database - the admin still confirms via the usual
    POST/PATCH .../address call (with the resulting latitude/longitude in the
    payload), so nothing is persisted just from looking up a suggestion.
    """
    await access.verify(tenant_id, current_user)

    result = await geocode_address(
        street=payload.street,
        city=payload.city,
        postal_code=payload.postal_code,
        province=payload.province,
        country=payload.country,
    )
    if result is None:
        return GeocodeResponse(confidence="not_found")

    return GeocodeResponse(
        latitude=result.latitude,
        longitude=result.longitude,
        display_name=result.display_name,
        confidence=result.confidence,  # type: ignore[arg-type]
    )


@router.delete("/{tenant_id}/address", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> None:
    """Delete address for a congregation."""
    await access.verify(tenant_id, current_user)

    await repo.delete_address(tenant_id)


# Service times endpoints
@router.get("/{tenant_id}/service-times", response_model=list[ServiceTimeResponse])
async def get_service_times(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> list[ServiceTimeResponse]:
    """Get all service times for a congregation."""
    await access.verify(tenant_id, current_user)

    service_times = await repo.get_service_times_by_tenant_id(tenant_id)
    return [
        ServiceTimeResponse(
            id=st.id,
            tenant_id=st.tenant_id,
            day=st.day,
            time=st.time,
            description=st.description,
            order=st.order,
            created_at=st.created_at,
        )
        for st in service_times
    ]


@router.post(
    "/{tenant_id}/service-times",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceTimeResponse,
)
async def create_service_time(
    tenant_id: str,
    payload: ServiceTimeCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> ServiceTimeResponse:
    """Create a service time for a congregation."""
    await access.verify(tenant_id, current_user)

    service_time = await repo.create_service_time(
        tenant_id=tenant_id,
        day=payload.day,
        time=payload.time,
        description=payload.description,
        order=payload.order,
    )

    return ServiceTimeResponse(
        id=service_time.id,
        tenant_id=service_time.tenant_id,
        day=service_time.day,
        time=service_time.time,
        description=service_time.description,
        order=service_time.order,
        created_at=service_time.created_at,
    )


@router.patch("/{tenant_id}/service-times/{service_time_id}", response_model=ServiceTimeResponse)
async def update_service_time(
    tenant_id: str,
    service_time_id: str,
    payload: ServiceTimeUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> ServiceTimeResponse:
    """Update a service time. Fields omitted from the request body are left
    unchanged; a field explicitly included (even as null, for `description`)
    is applied as given."""
    await access.verify(tenant_id, current_user)

    service_time = await repo.get_service_time_by_id(tenant_id, service_time_id)
    if not service_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service time {service_time_id} not found for tenant {tenant_id}",
        )

    # day/time/order map to non-nullable columns, so only apply them when a
    # real value is given. description is nullable, so it uses
    # model_fields_set instead to allow explicitly clearing it via `null`.
    if payload.day is not None:
        service_time.day = payload.day
    if payload.time is not None:
        service_time.time = payload.time
    if "description" in payload.model_fields_set:
        service_time.description = payload.description
    if payload.order is not None:
        service_time.order = payload.order

    await repo.db.commit()
    await repo.db.refresh(service_time)

    return ServiceTimeResponse(
        id=service_time.id,
        tenant_id=service_time.tenant_id,
        day=service_time.day,
        time=service_time.time,
        description=service_time.description,
        order=service_time.order,
        created_at=service_time.created_at,
    )


@router.delete(
    "/{tenant_id}/service-times/{service_time_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service_time(
    tenant_id: str,
    service_time_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> None:
    """Delete a service time."""
    await access.verify(tenant_id, current_user)

    if not await repo.delete_service_time(tenant_id, service_time_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service time {service_time_id} not found for tenant {tenant_id}",
        )


# Full congregation data endpoint
@router.get("/{tenant_id}/full", response_model=CongregationFullResponse)
async def get_full_congregation(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)],
) -> CongregationFullResponse:
    """Get full congregation data including address and service times."""
    await access.verify(tenant_id, current_user)

    address = await repo.get_address_by_tenant_id(tenant_id)
    service_times = await repo.get_service_times_by_tenant_id(tenant_id)

    return CongregationFullResponse(
        tenant_id=tenant_id,
        address=(
            AddressResponse(
                id=address.id,
                tenant_id=address.tenant_id,
                street=address.street,
                city=address.city,
                postal_code=address.postal_code,
                province=address.province,
                country=address.country,
                website=address.website,
                email=address.email,
                iban=address.iban,
                latitude=decode_coordinate(address.latitude),
                longitude=decode_coordinate(address.longitude),
                geocode_status=address.geocode_status,
                status=address.status,
                created_at=address.created_at,
                updated_at=address.updated_at,
                last_updated_at=address.last_updated_at,
                last_updated_label=address.last_updated_label,
            )
            if address
            else None
        ),
        service_times=[
            ServiceTimeResponse(
                id=st.id,
                tenant_id=st.tenant_id,
                day=st.day,
                time=st.time,
                description=st.description,
                order=st.order,
                created_at=st.created_at,
            )
            for st in service_times
        ],
    )


@router.get(
    "/{tenant_id}/change-log",
    response_model=ChangeLogResponse,
    summary="Change history for a congregation's address and contact data",
    description="Visible to admins, tenant members, and anyone with pastoral ACL access to this church (e.g. a regional bishop).",
)
async def get_change_log(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    acl_service: Annotated[AclService, Depends(get_acl_service)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ChangeLogResponse:
    await _verify_change_log_access(tenant_id, current_user, access, acl_service)

    rows = await repo.get_change_log(tenant_id, skip=skip, limit=limit)
    total = await repo.count_change_log_batches(tenant_id)
    return ChangeLogResponse(batches=_group_change_log_by_batch(rows), total=total)
