import type { IPersonSummary } from '../types/person.type'
import { apiClient } from './apiClient'

class PersonSearchService {
  async searchPersons(query: string): Promise<IPersonSummary[]> {
    const { data } = await apiClient.get<{ persons: IPersonSummary[] }>(
      '/churches/persons/search',
      { params: { q: query } },
    )
    return data.persons
  }
}

export const personSearchService = new PersonSearchService()
