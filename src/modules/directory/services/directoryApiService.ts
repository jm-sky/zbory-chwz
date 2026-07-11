import { apiClient } from '@/shared/services/apiClient'
import type {
  IDirectoryExportParams,
  IDirectoryFilters,
  IDirectoryPerson,
  IPersonBrowse,
  IPersonMergeRequest,
  IPersonUpdateRequest,
} from '../types/directory.types'

class DirectoryApiService {
  async getFilters(): Promise<IDirectoryFilters> {
    const { data } = await apiClient.get<IDirectoryFilters>('/people-directory/filters')
    return data
  }

  async exportPersons(params: IDirectoryExportParams): Promise<IDirectoryPerson[]> {
    const searchParams = new URLSearchParams()
    for (const id of params.regionIds) searchParams.append('regionIds', id)
    for (const id of params.serviceTypeIds) searchParams.append('serviceTypeIds', id)
    for (const id of params.groupIds) searchParams.append('groupIds', id)

    const { data } = await apiClient.get<{ persons: IDirectoryPerson[] }>(
      `/people-directory/export?${searchParams.toString()}`,
    )
    return data.persons
  }

  async listPersons(query?: string): Promise<IPersonBrowse[]> {
    const { data } = await apiClient.get<{ persons: IPersonBrowse[] }>(
      '/people-directory/persons',
      { params: query ? { q: query } : undefined },
    )
    return data.persons
  }

  async getPerson(personId: string): Promise<IPersonBrowse> {
    const { data } = await apiClient.get<IPersonBrowse>(
      `/people-directory/persons/${personId}`,
    )
    return data
  }

  async updatePerson(personId: string, payload: IPersonUpdateRequest): Promise<IPersonBrowse> {
    const { data } = await apiClient.patch<IPersonBrowse>(
      `/people-directory/persons/${personId}`,
      payload,
    )
    return data
  }

  async mergePersons(payload: IPersonMergeRequest): Promise<IPersonBrowse> {
    const { data } = await apiClient.post<IPersonBrowse>(
      '/people-directory/persons/merge',
      payload,
    )
    return data
  }
}

export const directoryApiService = new DirectoryApiService()
