import { apiClient } from '@/shared/services/apiClient'
import type {
  IGroup,
  IGroupCreateRequest,
  IGroupDetail,
  IGroupMembership,
  IGroupMembershipCreateRequest,
  IGroupMembershipUpdateRequest,
  IGroupUpdateRequest,
} from '../types/group.types'

class GroupApiService {
  async listGroups(): Promise<IGroup[]> {
    const { data } = await apiClient.get<IGroup[]>('/people-groups')
    return data
  }

  async getGroup(groupId: string): Promise<IGroupDetail> {
    const { data } = await apiClient.get<IGroupDetail>(`/people-groups/${groupId}`)
    return data
  }

  async createGroup(payload: IGroupCreateRequest): Promise<IGroup> {
    const { data } = await apiClient.post<IGroup>('/people-groups', payload)
    return data
  }

  async updateGroup(groupId: string, payload: IGroupUpdateRequest): Promise<IGroup> {
    const { data } = await apiClient.patch<IGroup>(`/people-groups/${groupId}`, payload)
    return data
  }

  async deleteGroup(groupId: string): Promise<void> {
    await apiClient.delete(`/people-groups/${groupId}`)
  }

  async addMembership(
    groupId: string,
    payload: IGroupMembershipCreateRequest,
  ): Promise<IGroupMembership> {
    const { data } = await apiClient.post<IGroupMembership>(
      `/people-groups/${groupId}/memberships`,
      payload,
    )
    return data
  }

  async updateMembership(
    groupId: string,
    membershipId: string,
    payload: IGroupMembershipUpdateRequest,
  ): Promise<IGroupMembership> {
    const { data } = await apiClient.patch<IGroupMembership>(
      `/people-groups/${groupId}/memberships/${membershipId}`,
      payload,
    )
    return data
  }

  async removeMembership(groupId: string, membershipId: string): Promise<void> {
    await apiClient.delete(`/people-groups/${groupId}/memberships/${membershipId}`)
  }
}

export const groupApiService = new GroupApiService()
