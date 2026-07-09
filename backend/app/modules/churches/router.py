"""API router for church hierarchy."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.schemas import (
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
    ChurchResponse,
    PersonResponse,
    PersonSearchResponse,
    RegionResponse,
    ServiceAssignmentCreateRequest,
    ServiceAssignmentResponse,
    ServiceAssignmentUpdateRequest,
    ServiceTypeResponse,
)
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository

router = APIRouter(prefix="/churches", tags=["Churches"])


async def _verify_church_access(
    church_id: str,
    current_user: CurrentUser,
    church_repo: ChurchRepository,
    tenant_repo: TenantRepository,
) -> None:
    church = await church_repo.ensure_church_access(church_id)
    tenant = await tenant_repo.get_tenant(church_id)
    if not tenant:
        return
    memberships = await tenant_repo.list_for_user(current_user.id)
    if any(m.tenant_id == church_id for _, m in memberships):
        return
    if current_user.isAdmin or current_user.isOwner:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/service-types", response_model=list[ServiceTypeResponse])
async def list_service_types(
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
) -> list[ServiceTypeResponse]:
    _ = current_user
    types = await repo.list_service_types()
    return [ServiceTypeResponse.model_validate(t) for t in types]


@router.get("/regions", response_model=list[RegionResponse])
async def list_regions(
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
) -> list[RegionResponse]:
    _ = current_user
    regions = await repo.list_regions()
    return [
        RegionResponse(
            id=r.id,
            communityId=r.community_id,
            name=r.name,
            slug=r.slug,
        )
        for r in regions
    ]


@router.get("/persons/search", response_model=PersonSearchResponse)
async def search_persons(
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    q: str = Query(min_length=1),
) -> PersonSearchResponse:
    _ = current_user
    persons = await repo.search_persons(q)
    return PersonSearchResponse(
        persons=[
            PersonResponse(
                id=p.id,
                firstName=p.first_name,
                lastName=p.last_name,
                email=p.email,
                phone=p.phone,
                userId=p.user_id,
            )
            for p in persons
        ]
    )


@router.get("/{church_id}", response_model=ChurchResponse)
async def get_church(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> ChurchResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    church = await repo.ensure_church_access(church_id)
    return ChurchResponse(
        id=church.id,
        communityId=church.community_id,
        regionId=church.region_id,
        tenantId=church.tenant_id,
        name=church.name,
        visibility=church.visibility,
        createdAt=church.created_at,
    )


@router.get("/{church_id}/branches", response_model=list[BranchResponse])
async def list_branches(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> list[BranchResponse]:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    branches = await repo.list_branches(church_id)
    return [
        BranchResponse(
            id=b.id,
            churchId=b.church_id,
            name=b.name,
            slug=b.slug,
            visibility=b.visibility,
            createdAt=b.created_at,
        )
        for b in branches
    ]


@router.post(
    "/{church_id}/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(
    church_id: str,
    payload: BranchCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> BranchResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    branch = await repo.create_branch(church_id, payload)
    return BranchResponse(
        id=branch.id,
        churchId=branch.church_id,
        name=branch.name,
        slug=branch.slug,
        visibility=branch.visibility,
        createdAt=branch.created_at,
    )


@router.patch("/{church_id}/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    church_id: str,
    branch_id: str,
    payload: BranchUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> BranchResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    branch = await repo.update_branch(branch_id, payload)
    if not branch or branch.church_id != church_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    return BranchResponse(
        id=branch.id,
        churchId=branch.church_id,
        name=branch.name,
        slug=branch.slug,
        visibility=branch.visibility,
        createdAt=branch.created_at,
    )


@router.delete("/{church_id}/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    church_id: str,
    branch_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    branches = await repo.list_branches(church_id)
    if not any(b.id == branch_id for b in branches):
        raise HTTPException(status_code=404, detail="Branch not found")
    await repo.delete_branch(branch_id)


def _assignment_response(assignment) -> ServiceAssignmentResponse:
    return ServiceAssignmentResponse.model_validate(assignment)


@router.get(
    "/{church_id}/service-assignments",
    response_model=list[ServiceAssignmentResponse],
)
async def list_service_assignments(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> list[ServiceAssignmentResponse]:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    assignments = await repo.list_service_assignments("church", church_id)
    return [_assignment_response(a) for a in assignments]


@router.post(
    "/{church_id}/service-assignments",
    response_model=ServiceAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_assignment(
    church_id: str,
    payload: ServiceAssignmentCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> ServiceAssignmentResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    assignment = await repo.create_service_assignment("church", church_id, payload)
    return _assignment_response(assignment)


@router.patch(
    "/{church_id}/service-assignments/{assignment_id}",
    response_model=ServiceAssignmentResponse,
)
async def update_service_assignment(
    church_id: str,
    assignment_id: str,
    payload: ServiceAssignmentUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> ServiceAssignmentResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    assignment = await repo.update_service_assignment(assignment_id, payload)
    if not assignment or assignment.scope_id != church_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return _assignment_response(assignment)


@router.delete(
    "/{church_id}/service-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service_assignment(
    church_id: str,
    assignment_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    assignments = await repo.list_service_assignments("church", church_id)
    if not any(a.id == assignment_id for a in assignments):
        raise HTTPException(status_code=404, detail="Assignment not found")
    await repo.delete_service_assignment(assignment_id)
