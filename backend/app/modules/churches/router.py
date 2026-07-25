"""API router for church hierarchy."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.acl_seed import Permission
from app.modules.churches.db_models import ServiceAssignmentDB
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.schemas import (
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
    ChurchCreateRequest,
    ChurchCreateResponse,
    ChurchMoveRegionRequest,
    ChurchResponse,
    ChurchVisibilityUpdateRequest,
    MePermissionsResponse,
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


async def _require_church(
    church_id: str,
    permission: str,
    current_user: CurrentUser,
    church_repo: ChurchRepository,
    permission_service: PermissionService,
) -> None:
    church = await church_repo.get_church_by_id(church_id)
    if not church:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Church not found")
    if not await permission_service.resolve(current_user, permission, ("church", church_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/me/permissions", response_model=MePermissionsResponse)
async def get_my_permissions(
    current_user: CurrentUser,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> MePermissionsResponse:
    payload = await permission_service.permissions_for_user(current_user)
    return MePermissionsResponse.model_validate(payload)


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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    q: str = Query(min_length=1),
) -> PersonSearchResponse:
    if not await permission_service.has_anywhere(current_user, Permission.SERVICES_MANAGE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    allowed_church_ids = await directory_repo.get_allowed_church_ids(
        current_user,
        Permission.SERVICES_MANAGE,
        permission_service=permission_service,
    )
    persons = await repo.search_persons(q, allowed_church_ids)
    return PersonSearchResponse(persons=[PersonResponse.model_validate(p) for p in persons])


@router.post("", response_model=ChurchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_church(
    payload: ChurchCreateRequest,
    current_user: CurrentUser,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    church_repo: Annotated[ChurchRepository, Depends(get_church_repository)],
) -> ChurchCreateResponse:
    if not await permission_service.has_anywhere(current_user, Permission.CHURCH_CREATE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    region_id, warning = await church_repo.resolve_create_region(
        current_user,
        permission_service,
        payload.regionId,
    )

    tenant, _membership = await tenant_repo.create_tenant(
        name=payload.name,
        description=payload.description,
        owner_user_id=current_user.id,
    )
    church = await provision_church_for_tenant(church_repo.db, tenant)
    if region_id:
        church.region_id = region_id

    from app.modules.churches.bishop_seed import ensure_pastor_acl_for_owner

    await ensure_pastor_acl_for_owner(
        church_repo.db,
        user_id=current_user.id,
        church_id=church.id,
    )
    await church_repo.db.commit()

    return ChurchCreateResponse(
        id=church.id,
        name=church.name,
        regionId=church.region_id,
        warning=warning,
    )


@router.get("/{church_id}", response_model=ChurchResponse)
async def get_church(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ChurchResponse:
    await _require_church(church_id, Permission.CHURCH_VIEW, current_user, repo, permission_service)
    church = await repo.ensure_church_access(church_id)
    return ChurchResponse.model_validate(church)


@router.patch("/{church_id}/visibility", response_model=ChurchResponse)
async def update_church_visibility(
    church_id: str,
    payload: ChurchVisibilityUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ChurchResponse:
    await _require_church(church_id, Permission.CHURCH_PUBLISH, current_user, repo, permission_service)
    church = await repo.update_visibility(church_id, payload.visibility)
    if not church:
        raise HTTPException(status_code=404, detail="Church not found")
    return ChurchResponse.model_validate(church)


@router.patch("/{church_id}/region", response_model=ChurchResponse)
async def move_church_region(
    church_id: str,
    payload: ChurchMoveRegionRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ChurchResponse:
    await _require_church(church_id, Permission.CHURCH_MOVE_REGION, current_user, repo, permission_service)
    church = await repo.move_region(church_id, payload.regionId, permission_service.cache)
    if not church:
        raise HTTPException(status_code=404, detail="Church not found")
    return ChurchResponse.model_validate(church)


@router.get("/{church_id}/branches", response_model=list[BranchResponse])
async def list_branches(
    church_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> list[BranchResponse]:
    await _require_church(church_id, Permission.CHURCH_VIEW, current_user, repo, permission_service)
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> BranchResponse:
    await _require_church(church_id, Permission.BRANCH_MANAGE, current_user, repo, permission_service)
    branch = await repo.create_branch(church_id, payload)
    return BranchResponse.model_validate(branch)


@router.patch("/{church_id}/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    church_id: str,
    branch_id: str,
    payload: BranchUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> BranchResponse:
    await _require_church(church_id, Permission.BRANCH_MANAGE, current_user, repo, permission_service)
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    await _require_church(church_id, Permission.BRANCH_MANAGE, current_user, repo, permission_service)
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> list[ServiceAssignmentResponse]:
    await _require_church(church_id, Permission.CHURCH_VIEW, current_user, repo, permission_service)
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ServiceAssignmentResponse:
    await _require_church(church_id, Permission.PEOPLE_MANAGE, current_user, repo, permission_service)
    assignment = await repo.create_service_assignment(
        "church",
        church_id,
        payload,
        actor=current_user,
        permission_service=permission_service,
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> ServiceAssignmentResponse:
    await _require_church(church_id, Permission.PEOPLE_MANAGE, current_user, repo, permission_service)
    assignment = await repo.update_service_assignment(
        "church",
        church_id,
        assignment_id,
        payload,
        actor=current_user,
        permission_service=permission_service,
    )
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
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    await _require_church(church_id, Permission.PEOPLE_MANAGE, current_user, repo, permission_service)
    if not await repo.delete_service_assignment("church", church_id, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
