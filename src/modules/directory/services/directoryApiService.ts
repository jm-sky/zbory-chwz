import { apiClient } from '@/shared/services/apiClient'
import type {
  IDirectoryExportParams,
  IDirectoryFilters,
  IDirectoryPerson,
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
}

export const directoryApiService = new DirectoryApiService()
