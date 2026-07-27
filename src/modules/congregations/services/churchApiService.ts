import { apiClient } from '@/shared/services/apiClient'
import type {
  IBranch,
  IBranchCreateRequest,
  IGrantableRole,
  IInviteResponse,
  IPerson,
  IServiceAssignment,
  IServiceAssignmentCreateRequest,
  IServiceAssignmentUpdateRequest,
  IServiceType,
} from '../types/church.types'

class ChurchApiService {
  async listServiceTypes(): Promise<IServiceType[]> {
    const { data } = await apiClient.get<IServiceType[]>('/churches/service-types')
    return data
  }

  async listGrantableRoles(scopeType: string, scopeId: string): Promise<IGrantableRole[]> {
    const { data } = await apiClient.get<IGrantableRole[]>('/churches/grantable-roles', {
      params: { scopeType, scopeId },
    })
    return data
  }

  async listRoles(): Promise<IGrantableRole[]> {
    const { data } = await apiClient.get<IGrantableRole[]>('/churches/roles')
    return data
  }

  async searchPersons(query: string): Promise<IPerson[]> {
    const { data } = await apiClient.get<{ persons: IPerson[] }>(
      '/churches/persons/search',
      { params: { q: query } },
    )
    return data.persons
  }

  async listBranches(churchId: string): Promise<IBranch[]> {
    const { data } = await apiClient.get<IBranch[]>(`/churches/${churchId}/branches`)
    return data
  }

  async createBranch(churchId: string, payload: IBranchCreateRequest): Promise<IBranch> {
    const { data } = await apiClient.post<IBranch>(`/churches/${churchId}/branches`, payload)
    return data
  }

  async deleteBranch(churchId: string, branchId: string): Promise<void> {
    await apiClient.delete(`/churches/${churchId}/branches/${branchId}`)
  }

  async listServiceAssignments(churchId: string): Promise<IServiceAssignment[]> {
    const { data } = await apiClient.get<IServiceAssignment[]>(
      `/churches/${churchId}/service-assignments`,
    )
    return data
  }

  async createServiceAssignment(
    churchId: string,
    payload: IServiceAssignmentCreateRequest,
  ): Promise<IServiceAssignment> {
    const { data } = await apiClient.post<IServiceAssignment>(
      `/churches/${churchId}/service-assignments`,
      payload,
    )
    return data
  }

  async updateServiceAssignment(
    churchId: string,
    assignmentId: string,
    payload: IServiceAssignmentUpdateRequest,
  ): Promise<IServiceAssignment> {
    const { data } = await apiClient.patch<IServiceAssignment>(
      `/churches/${churchId}/service-assignments/${assignmentId}`,
      payload,
    )
    return data
  }

  async deleteServiceAssignment(churchId: string, assignmentId: string): Promise<void> {
    await apiClient.delete(`/churches/${churchId}/service-assignments/${assignmentId}`)
  }

  async inviteServiceAssignment(churchId: string, assignmentId: string): Promise<IInviteResponse> {
    const { data } = await apiClient.post<IInviteResponse>(
      `/churches/${churchId}/service-assignments/${assignmentId}/invite`,
    )
    return data
  }
}

export const churchApiService = new ChurchApiService()
