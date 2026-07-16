import { isAxiosError } from 'axios'
import { apiClient } from '@/shared/services/apiClient'
import type {
  IDirectoryExportParams,
  IDirectoryFilters,
  IDirectoryPerson,
  IPersonBrowse,
  IPersonChangeLogResponse,
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

  /**
   * Change history for a person's directory record. Returns null when the
   * current user has no ACL access to the people directory - the caller
   * should simply hide the section, not show an error.
   */
  async getChangeLog(personId: string): Promise<IPersonChangeLogResponse | null> {
    try {
      const { data } = await apiClient.get<IPersonChangeLogResponse>(
        `/people-directory/persons/${personId}/change-log`,
      )
      return data
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 403) {
        return null
      }
      throw error
    }
  }
}

export const directoryApiService = new DirectoryApiService()
