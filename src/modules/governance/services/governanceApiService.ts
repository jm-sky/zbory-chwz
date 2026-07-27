import { apiClient } from '@/shared/services/apiClient'
import type {
  IAclAuditLogResponse,
  IRoleAssignment,
  IRoleAssignmentCreateRequest,
  IUserPermission,
  IUserPermissionUpsertRequest,
} from '../types/governance.types'

class GovernanceApiService {
  async listRoleAssignments(scopeType: string, scopeId: string): Promise<IRoleAssignment[]> {
    const { data } = await apiClient.get<IRoleAssignment[]>('/governance/role-assignments', {
      params: { scopeType, scopeId },
    })
    return data
  }

  async createRoleAssignment(payload: IRoleAssignmentCreateRequest): Promise<IRoleAssignment> {
    const { data } = await apiClient.post<IRoleAssignment>('/governance/role-assignments', payload)
    return data
  }

  async deleteRoleAssignment(assignmentId: string): Promise<void> {
    await apiClient.delete(`/governance/role-assignments/${assignmentId}`)
  }

  async listUserPermissions(userId: string, scopeType: string, scopeId: string): Promise<IUserPermission[]> {
    const { data } = await apiClient.get<IUserPermission[]>('/governance/user-permissions', {
      params: { userId, scopeType, scopeId },
    })
    return data
  }

  async upsertUserPermission(payload: IUserPermissionUpsertRequest): Promise<IUserPermission> {
    const { data } = await apiClient.put<IUserPermission>('/governance/user-permissions', payload)
    return data
  }

  async deleteUserPermission(exceptionId: string): Promise<void> {
    await apiClient.delete(`/governance/user-permissions/${exceptionId}`)
  }

  async listAuditLog(
    scopeType: string,
    scopeId: string,
    params: { targetUserId?: string, skip: number, limit: number },
  ): Promise<IAclAuditLogResponse> {
    const { data } = await apiClient.get<IAclAuditLogResponse>('/governance/audit-log', {
      params: { scopeType, scopeId, ...params },
    })
    return data
  }
}

export const governanceApiService = new GovernanceApiService()
