"""API router for congregation management (addresses, service times)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.congregations.geo import is_valid_province
from app.modules.congregations.repositories import (
    CongregationRepository,
    get_congregation_repository,
)
from app.modules.congregations.schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
    CongregationFullResponse,
    ServiceTimeCreateRequest,
    ServiceTimeResponse,
)
from app.modules.tenants.access import verify_tenant_access
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository

router = APIRouter(prefix="/congregations", tags=["Congregations"])


# Address endpoints
@router.get("/{tenant_id}/address", response_model=AddressResponse)
async def get_address(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> AddressResponse:
    """Get address for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

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
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
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
) -> AddressResponse:
    """Create or update address for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    address = await repo.create_or_update_address(
        tenant_id=tenant_id,
        street=payload.street,
        city=payload.city,
        postal_code=payload.postal_code,
        province=payload.province,
        country=payload.country,
        status=payload.status,
    )

    return AddressResponse(
        id=address.id,
        tenant_id=address.tenant_id,
        street=address.street,
        city=address.city,
        postal_code=address.postal_code,
        province=address.province,
        country=address.country,
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
    )


@router.patch("/{tenant_id}/address", response_model=AddressResponse)
async def update_address(
    tenant_id: str,
    payload: AddressUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> AddressResponse:
    """Update address for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    address = await repo.get_address_by_tenant_id(tenant_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address not found for tenant {tenant_id}",
        )

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

    return AddressResponse(
        id=address.id,
        tenant_id=address.tenant_id,
        street=address.street,
        city=address.city,
        postal_code=address.postal_code,
        province=address.province,
        country=address.country,
        status=address.status,
        created_at=address.created_at,
        updated_at=address.updated_at,
    )


@router.delete("/{tenant_id}/address", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    """Delete address for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    await repo.delete_address(tenant_id)


# Service times endpoints
@router.get("/{tenant_id}/service-times", response_model=list[ServiceTimeResponse])
async def get_service_times(
    tenant_id: str,
    current_user: CurrentUser,
    repo: Annotated[CongregationRepository, Depends(get_congregation_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> list[ServiceTimeResponse]:
    """Get all service times for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    service_times = await repo.get_service_times_by_tenant_id(tenant_id)
    return [
        ServiceTimeResponse(
            id=st.id,
            tenant_id=st.tenant_id,
            day=st.day,
            time=st.time,
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
) -> ServiceTimeResponse:
    """Create a service time for a congregation."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

    service_time = await repo.create_service_time(
        tenant_id=tenant_id,
        day=payload.day,
        time=payload.time,
        order=payload.order,
    )

    return ServiceTimeResponse(
        id=service_time.id,
        tenant_id=service_time.tenant_id,
        day=service_time.day,
        time=service_time.time,
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
) -> None:
    """Delete a service time."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

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
) -> CongregationFullResponse:
    """Get full congregation data including address and service times."""
    await verify_tenant_access(tenant_id, current_user, tenant_repo)

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
                status=address.status,
                created_at=address.created_at,
                updated_at=address.updated_at,
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
                order=st.order,
                created_at=st.created_at,
            )
            for st in service_times
        ],
    )
