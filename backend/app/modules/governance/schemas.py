"""Pydantic schemas for the governance module (role assignments G5, permission
exceptions G9)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PermissionEffect = Literal["allow", "deny"]


class RoleAssignmentResponse(BaseModel):
    """Always built explicitly (see governance/router.py._role_assignment_response) from a
    UserRoleAssignmentDB + its joined role name — not via model_validate(orm_object), since
    roleName comes from a relationship, not a column. No aliases needed as a result."""

    id: str
    userId: str
    roleName: str
    scopeType: str
    scopeId: str
    sourceAssignmentId: str | None = None
    createdAt: datetime


class RoleAssignmentCreateRequest(BaseModel):
    userId: str
    roleName: str
    scopeType: str
    scopeId: str


class UserPermissionResponse(BaseModel):
    """Always built explicitly, matching RoleAssignmentResponse — see
    governance/router.py._user_permission_response."""

    id: str
    userId: str
    scopeType: str
    scopeId: str
    permission: str
    effect: PermissionEffect
    sourceAssignmentId: str | None = None
    createdBy: str | None = None
    createdAt: datetime


class UserPermissionUpsertRequest(BaseModel):
    userId: str
    scopeType: str
    scopeId: str
    permission: str
    effect: PermissionEffect


class AclAuditEntryResponse(BaseModel):
    """One row of the append-only audit log (G8) — always built explicitly from an
    AclAuditLogDB row, matching RoleAssignmentResponse/UserPermissionResponse."""

    id: str
    targetUserId: str | None
    targetLabel: str
    action: str
    scopeType: str | None
    scopeId: str | None
    roleName: str | None
    permission: str | None
    effect: str | None
    oldValue: str | None
    newValue: str | None


class AclAuditBatchResponse(BaseModel):
    """One action (e.g. one grant, or one cascading assignment delete), grouping every
    row it wrote — mirrors PersonChangeLogBatch (directory/schemas.py)."""

    batchId: str
    source: str
    actorLabel: str
    createdAt: datetime
    entries: list[AclAuditEntryResponse]


class AclAuditLogResponse(BaseModel):
    batches: list[AclAuditBatchResponse]
    total: int
