import { useQuery } from '@tanstack/vue-query'
import { congregationApiService } from '../services/congregationApiService'

/**
 * Composable for fetching congregations list
 */
export function useCongregations() {
  return useQuery({
    queryKey: ['congregations'],
    queryFn: () => congregationApiService.getCongregations(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
