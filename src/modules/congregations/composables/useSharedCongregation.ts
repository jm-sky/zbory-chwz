import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import type { IShareResolveResponse } from '../types/shareLink.types'
import { shareLinkApiService } from '../services/shareLinkApiService'

/**
 * Resolves a share link token to either a single congregation or an
 * all-congregations list. Never retries: an invalid/expired/revoked token
 * will not become valid on retry.
 */
export function useSharedCongregation(token: MaybeRefOrGetter<string>) {
  return useQuery<IShareResolveResponse>({
    queryKey: computed(() => ['share', toValue(token)]),
    queryFn: () => shareLinkApiService.resolve(toValue(token)),
    enabled: computed(() => !!toValue(token)),
    retry: false,
  })
}
