import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import type { IShareLinkCreateRequest } from '../types/shareLink.types'
import { shareLinkApiService } from '../services/shareLinkApiService'

export const shareLinkQueryKeys = {
  all: (tenantId: string | null) => (tenantId ? (['congregations', tenantId, 'share-links'] as const) : (['share-links', 'global'] as const)),
}

/** tenantId null fetches the current admin/owner's all-congregations links. */
export function useShareLinks(tenantId: MaybeRefOrGetter<string | null>) {
  return useQuery({
    queryKey: computed(() => shareLinkQueryKeys.all(toValue(tenantId))),
    queryFn: () => shareLinkApiService.list(toValue(tenantId)),
    enabled: computed(() => toValue(tenantId) !== ''),
  })
}

export function useCreateShareLink(tenantId: MaybeRefOrGetter<string | null>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: IShareLinkCreateRequest) => shareLinkApiService.create(toValue(tenantId), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shareLinkQueryKeys.all(toValue(tenantId)) })
    },
  })
}

export function useRevokeShareLink(tenantId: MaybeRefOrGetter<string | null>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (linkId: string) => shareLinkApiService.revoke(toValue(tenantId), linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shareLinkQueryKeys.all(toValue(tenantId)) })
    },
  })
}
