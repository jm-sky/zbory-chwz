export type GovernanceScopeType = 'community' | 'region' | 'church' | 'branch'

export interface IGovernanceScope {
  scopeType: GovernanceScopeType
  scopeId: string
  label: string
}

export interface IRoleAssignment {
  id: string
  userId: string
  roleName: string
  scopeType: string
  scopeId: string
  sourceAssignmentId: string | null
  createdAt: string
}

export interface IRoleAssignmentCreateRequest {
  userId: string
  roleName: string
  scopeType: string
  scopeId: string
}

/** Tri-state: whether an exception overrides the role-derived permission, and how. */
export type PermissionEffectState = 'inherited' | 'allow' | 'deny'

export interface IUserPermission {
  id: string
  userId: string
  scopeType: string
  scopeId: string
  permission: string
  effect: 'allow' | 'deny'
  sourceAssignmentId: string | null
  createdBy: string | null
  createdAt: string
}

export interface IUserPermissionUpsertRequest {
  userId: string
  scopeType: string
  scopeId: string
  permission: string
  effect: 'allow' | 'deny'
}

export interface IAclAuditEntry {
  id: string
  targetUserId: string | null
  targetLabel: string
  action: string
  scopeType: string | null
  scopeId: string | null
  roleName: string | null
  permission: string | null
  effect: string | null
  oldValue: string | null
  newValue: string | null
}

export interface IAclAuditBatch {
  batchId: string
  source: string
  actorLabel: string
  createdAt: string
  entries: IAclAuditEntry[]
}

export interface IAclAuditLogResponse {
  batches: IAclAuditBatch[]
  total: number
}
