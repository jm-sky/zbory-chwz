import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import type { ICongregationDetail } from '../types/congregation.types'
import { congregationApiService } from '../services/congregationApiService'
import { congregationKeys } from '../utils/congregationKeys'

/**
 * Composable for fetching a single congregation's detail
 */
export function useCongregationDetail(id: MaybeRefOrGetter<string>) {
  return useQuery<ICongregationDetail>({
    queryKey: computed(() => congregationKeys.detail(toValue(id))),
    queryFn: () => congregationApiService.getCongregationDetail(toValue(id)),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: computed(() => !!toValue(id)),
  })
}
