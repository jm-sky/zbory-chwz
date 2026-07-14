import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import type { IShareLinkCreateRequest } from '../types/shareLink.types'
import { shareLinkApiService } from '../services/shareLinkApiService'

export const shareLinkQueryKeys = {
  all: (tenantId: string) => ['congregations', tenantId, 'share-links'] as const,
}

export function useShareLinks(tenantId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => shareLinkQueryKeys.all(toValue(tenantId))),
    queryFn: () => shareLinkApiService.list(toValue(tenantId)),
    enabled: computed(() => !!toValue(tenantId)),
  })
}

export function useCreateShareLink(tenantId: MaybeRefOrGetter<string>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: IShareLinkCreateRequest) => shareLinkApiService.create(toValue(tenantId), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shareLinkQueryKeys.all(toValue(tenantId)) })
    },
  })
}

export function useRevokeShareLink(tenantId: MaybeRefOrGetter<string>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (linkId: string) => shareLinkApiService.revoke(toValue(tenantId), linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shareLinkQueryKeys.all(toValue(tenantId)) })
    },
  })
}
