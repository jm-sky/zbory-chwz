import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import type { ICongregationDetail } from '../types/congregation.types'
import { shareLinkApiService } from '../services/shareLinkApiService'

/**
 * Fetches the read-only congregation view behind a share link token.
 * Never retries: an invalid/expired/revoked token will not become valid on retry.
 */
export function useSharedCongregation(token: MaybeRefOrGetter<string>) {
  return useQuery<ICongregationDetail>({
    queryKey: computed(() => ['share', toValue(token)]),
    queryFn: () => shareLinkApiService.getSharedCongregation(toValue(token)),
    enabled: computed(() => !!toValue(token)),
    retry: false,
  })
}
