"""API router for governance role assignments (G5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.churches.acl_models import UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission
from app.modules.churches.permission_service import PermissionService, get_permission_service
from app.modules.governance.db_models import AclAuditLogDB
from app.modules.governance.repositories import (
    GovernanceRepository,
    get_governance_repository,
)
from app.modules.governance.schemas import (
    AclAuditBatchResponse,
    AclAuditEntryResponse,
    AclAuditLogResponse,
    RoleAssignmentCreateRequest,
    RoleAssignmentResponse,
    UserPermissionResponse,
    UserPermissionUpsertRequest,
)

router = APIRouter(prefix="/governance", tags=["Governance"])


def _role_assignment_response(assignment: UserRoleAssignmentDB) -> RoleAssignmentResponse:
    return RoleAssignmentResponse(
        id=assignment.id,
        userId=assignment.user_id,
        roleName=assignment.role.name,
        scopeType=assignment.scope_type,
        scopeId=assignment.scope_id,
        sourceAssignmentId=assignment.source_assignment_id,
        createdAt=assignment.created_at,
    )


def _user_permission_response(row: UserPermissionDB) -> UserPermissionResponse:
    return UserPermissionResponse(
        id=row.id,
        userId=row.user_id,
        scopeType=row.scope_type,
        scopeId=row.scope_id,
        permission=row.permission,
        effect=row.effect,  # type: ignore[arg-type]
        sourceAssignmentId=row.source_assignment_id,
        createdBy=row.created_by,
        createdAt=row.created_at,
    )


def _group_audit_log_by_batch(rows: list[AclAuditLogDB]) -> list[AclAuditBatchResponse]:
    """Groups flat audit rows into batches keyed by batch_id — same convention as
    _group_person_change_log_by_batch (directory/router.py). `rows` is already ordered
    created_at desc; source/actor_label are taken from the first row seen per batch and
    createdAt is the max across the batch."""
    batches: dict[str, AclAuditBatchResponse] = {}
    order: list[str] = []
    for row in rows:
        batch = batches.get(row.batch_id)
        entry = AclAuditEntryResponse(
            id=row.id,
            targetUserId=row.target_user_id,
            targetLabel=row.target_label,
            action=row.action,
            scopeType=row.scope_type,
            scopeId=row.scope_id,
            roleName=row.role_name,
            permission=row.permission,
            effect=row.effect,
            oldValue=row.old_value,
            newValue=row.new_value,
        )
        if batch is None:
            batches[row.batch_id] = AclAuditBatchResponse(
                batchId=row.batch_id,
                source=row.source,
                actorLabel=row.actor_label,
                createdAt=row.created_at,
                entries=[entry],
            )
            order.append(row.batch_id)
        else:
            batch.entries.append(entry)
            if row.created_at > batch.createdAt:
                batch.createdAt = row.created_at

    return sorted((batches[batch_id] for batch_id in order), key=lambda b: b.createdAt, reverse=True)


@router.get("/role-assignments", response_model=list[RoleAssignmentResponse])
async def list_role_assignments(
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    scopeType: str = Query(...),
    scopeId: str = Query(...),
) -> list[RoleAssignmentResponse]:
    if not await permission_service.resolve(current_user, Permission.SERVICES_MANAGE, (scopeType, scopeId)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    assignments = await repo.list_role_assignments(scopeType, scopeId)
    return [_role_assignment_response(a) for a in assignments]


@router.post(
    "/role-assignments",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_assignment(
    payload: RoleAssignmentCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> RoleAssignmentResponse:
    assignment = await repo.create_role_assignment(
        actor=current_user,
        permission_service=permission_service,
        target_user_id=payload.userId,
        role_name=payload.roleName,
        scope_type=payload.scopeType,
        scope_id=payload.scopeId,
        cache=permission_service.cache,
    )
    return _role_assignment_response(assignment)


@router.delete(
    "/role-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role_assignment(
    assignment_id: str,
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    await repo.delete_role_assignment(
        actor=current_user,
        permission_service=permission_service,
        assignment_id=assignment_id,
        cache=permission_service.cache,
    )


@router.get("/user-permissions", response_model=list[UserPermissionResponse])
async def list_user_permissions(
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    userId: str = Query(...),
    scopeType: str = Query(...),
    scopeId: str = Query(...),
) -> list[UserPermissionResponse]:
    if not await permission_service.resolve(current_user, Permission.SERVICES_MANAGE, (scopeType, scopeId)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = await repo.list_user_permissions(userId, scopeType, scopeId)
    return [_user_permission_response(r) for r in rows]


@router.put("/user-permissions", response_model=UserPermissionResponse)
async def upsert_user_permission(
    payload: UserPermissionUpsertRequest,
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> UserPermissionResponse:
    row = await repo.upsert_user_permission(
        actor=current_user,
        permission_service=permission_service,
        target_user_id=payload.userId,
        scope_type=payload.scopeType,
        scope_id=payload.scopeId,
        permission=payload.permission,
        effect=payload.effect,
        cache=permission_service.cache,
    )
    return _user_permission_response(row)


@router.delete(
    "/user-permissions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user_permission(
    exception_id: str,
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    await repo.delete_user_permission(
        actor=current_user,
        permission_service=permission_service,
        exception_id=exception_id,
        cache=permission_service.cache,
    )


@router.get("/audit-log", response_model=AclAuditLogResponse)
async def get_audit_log(
    current_user: CurrentUser,
    repo: Annotated[GovernanceRepository, Depends(get_governance_repository)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    scopeType: str = Query(...),
    scopeId: str = Query(...),
    targetUserId: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> AclAuditLogResponse:
    """Append-only — there is deliberately no PUT/PATCH/DELETE for this log (G8)."""
    if not (current_user.isAdmin or current_user.isOwner):
        if not await permission_service.resolve(current_user, Permission.SERVICES_MANAGE, (scopeType, scopeId)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = await repo.list_audit_log(scope_type=scopeType, scope_id=scopeId, target_user_id=targetUserId, skip=skip, limit=limit)
    total = await repo.count_audit_log_batches(scope_type=scopeType, scope_id=scopeId, target_user_id=targetUserId)
    return AclAuditLogResponse(batches=_group_audit_log_by_batch(rows), total=total)
