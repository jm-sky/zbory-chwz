"""API router for church hierarchy."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.db_models import ServiceAssignmentDB
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
from app.modules.directory.repositories import (
    DirectoryRepository,
    get_directory_repository,
)
from app.modules.tenants.repositories import TenantRepository, get_tenant_repository

router = APIRouter(prefix="/churches", tags=["Churches"])


async def _verify_church_access(
    church_id: str,
    current_user: CurrentUser,
    church_repo: ChurchRepository,
    tenant_repo: TenantRepository,
) -> None:
    await church_repo.ensure_church_access(church_id)

    if current_user.isAdmin or current_user.isOwner:
        return

    memberships = await tenant_repo.list_for_user(current_user.id)
    if any(m.tenant_id == church_id for _, m in memberships):
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
    return [RegionResponse.model_validate(r) for r in regions]


@router.get("/persons/search", response_model=PersonSearchResponse)
@rate_limit("30/minute")
async def search_persons(
    request: Request,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    directory_repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
    q: str = Query(min_length=1),
) -> PersonSearchResponse:
    """Search persons, scoped to churches the caller has ACL access to.

    Admins/owners get an unrestricted search (allowed_church_ids=None); everyone
    else is limited to their church/region/community scope, same as
    /people-directory/persons.
    """
    allowed_church_ids = await directory_repo.get_allowed_church_ids(current_user)
    persons = await repo.search_persons(q, allowed_church_ids)
    return PersonSearchResponse(persons=[PersonResponse.model_validate(p) for p in persons])


@router.get("/{church_id}", response_model=ChurchResponse)
async def get_church(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> ChurchResponse:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    church = await repo.ensure_church_access(church_id)
    return ChurchResponse.model_validate(church)


@router.get("/{church_id}/branches", response_model=list[BranchResponse])
async def list_branches(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> list[BranchResponse]:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    branches = await repo.list_branches(church_id)
    return [BranchResponse.model_validate(b) for b in branches]


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
    return BranchResponse.model_validate(branch)


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
    branch = await repo.update_branch(church_id, branch_id, payload)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return BranchResponse.model_validate(branch)


@router.delete("/{church_id}/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    church_id: str,
    branch_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> None:
    await _verify_church_access(church_id, current_user, repo, tenant_repo)
    if not await repo.delete_branch(church_id, branch_id):
        raise HTTPException(status_code=404, detail="Branch not found")


def _assignment_response(assignment: ServiceAssignmentDB) -> ServiceAssignmentResponse:
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
    assignment = await repo.create_service_assignment(
        "church",
        church_id,
        payload,
        can_grant_elevated_roles=current_user.isAdmin or current_user.isOwner,
    )
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
    assignment = await repo.update_service_assignment("church", church_id, assignment_id, payload)
    if not assignment:
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
    if not await repo.delete_service_assignment("church", church_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
