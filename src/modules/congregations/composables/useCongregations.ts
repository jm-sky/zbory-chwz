import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import type { ICongregationDetailed } from '../types/congregation.types'
import { congregationApiService } from '../services/congregationApiService'
import { congregationKeys } from '../utils/congregationKeys'

/**
 * Composable for fetching congregations list
 */
export function useCongregations() {
  const authStore = useAuthStore()
  const isAuthenticated = computed<boolean>(() => !!authStore.user)

  return useQuery<ICongregationDetailed[]>({
    // Plain boolean in the key (via toValue in congregationKeys) so
    // invalidateQueries({ queryKey: congregationKeys.all }) always matches.
    queryKey: computed(() => congregationKeys.list(isAuthenticated.value)),
    queryFn: () => congregationApiService.getCongregationsDetailed(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
