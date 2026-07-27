"""API router for church hierarchy."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.email.service import get_email_service
from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.acl_grant_rules import assert_can_assign_service_type, can_grant_role
from app.modules.churches.acl_seed import ROLE_SEED, Permission
from app.modules.churches.db_models import ServiceAssignmentDB
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.repositories import ChurchRepository, get_church_repository
from app.modules.churches.schemas import (
    AccountState,
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
    ChurchCreateRequest,
    ChurchCreateResponse,
    ChurchMoveRegionRequest,
    ChurchResponse,
    ChurchVisibilityUpdateRequest,
    GrantableRoleResponse,
    InviteResponse,
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

logger = logging.getLogger(__name__)

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
    await permission_service.cache.invalidate_user(current_user.id)

    return ChurchCreateResponse(
        id=church.id,
        name=church.name,
        regionId=church.region_id,
        warning=warning,
    )


@router.get("/roles", response_model=list[GrantableRoleResponse])
async def list_roles(current_user: CurrentUser) -> list[GrantableRoleResponse]:
    """Full ACL role catalog (ROLE_SEED), for UI displaying "what this role grants" —
    not filtered by the caller's own grant authority (see /grantable-roles for that)."""
    _ = current_user
    return [GrantableRoleResponse(name=name, scopeType=scope_type, permissions=[str(p) for p in permissions]) for name, scope_type, permissions in ROLE_SEED]


@router.get("/grantable-roles", response_model=list[GrantableRoleResponse])
async def list_grantable_roles(
    current_user: CurrentUser,
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    scopeType: str = Query(...),
    scopeId: str = Query(...),
) -> list[GrantableRoleResponse]:
    chain = await permission_service.scope_chain(scopeType, scopeId)
    community_id = next((sid for st, sid in chain if st == "community"), None)
    if not community_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")

    grantable: list[GrantableRoleResponse] = []
    for name, role_scope_type, permissions in ROLE_SEED:
        if role_scope_type != scopeType:
            continue
        if await can_grant_role(
            permission_service,
            current_user,
            name,
            (scopeType, scopeId),
            community_id=community_id,
        ):
            grantable.append(
                GrantableRoleResponse(
                    name=name,
                    scopeType=role_scope_type,
                    permissions=[str(p) for p in permissions],
                )
            )
    return grantable


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


def _assignment_response(assignment: ServiceAssignmentDB, account: AccountState | None = None) -> ServiceAssignmentResponse:
    response = ServiceAssignmentResponse.model_validate(assignment)
    response.account = account
    return response


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
    persons = [a.person for a in assignments if a.person]
    account_states = await repo.get_account_states(persons)
    return [_assignment_response(a, account_states.get(a.person_id)) for a in assignments]


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
    account_states = await repo.get_account_states([assignment.person] if assignment.person else [])
    return _assignment_response(assignment, account_states.get(assignment.person_id))


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
    account_states = await repo.get_account_states([assignment.person] if assignment.person else [])
    return _assignment_response(assignment, account_states.get(assignment.person_id))


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
    result = await repo.delete_service_assignment("church", church_id, assignment_id, cache=permission_service.cache, actor=current_user)
    if not result.deleted:
        raise HTTPException(status_code=404, detail="Assignment not found")


@router.post(
    "/{church_id}/service-assignments/{assignment_id}/invite",
    response_model=InviteResponse,
)
@rate_limit("10/hour")
async def invite_service_assignment(
    request: Request,
    church_id: str,
    assignment_id: str,
    current_user: CurrentUser,
    repo: Annotated[ChurchRepository, Depends(get_church_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> InviteResponse:
    church = await repo.ensure_church_access(church_id)
    assignment = await repo.get_service_assignment("church", church_id, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    # Same permission the assignment itself required — not a hardcoded people.manage (§010).
    await assert_can_assign_service_type(
        permission_service,
        current_user,
        ("church", church_id),
        assignment.service_type,
        community_id=church.community_id,
    )

    invite = await repo.invite_assignment_account(assignment, actor=current_user)

    try:
        email_service = get_email_service()
        await email_service.send_invitation_email(
            to=invite.email,
            name=invite.name,
            invite_token=invite.token,
            user_id=invite.user_id,
        )
    except Exception:
        logger.exception("Failed to send invitation email to user %s", invite.user_id)

    return InviteResponse(invitedAt=invite.invited_at, invitationExpiresAt=invite.expires_at)
