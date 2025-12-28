import { useQuery } from '@tanstack/vue-query'
import type { ICongregationDetailed } from '../types/congregation.types'
import { congregationApiService } from '../services/congregationApiService'

/**
 * Composable for fetching congregations list
 */
export function useCongregations() {
  return useQuery<ICongregationDetailed[]>({
    queryKey: ['congregations', 'detailed'],
    queryFn: () => congregationApiService.getCongregationsDetailed(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
