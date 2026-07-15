import { apiClient } from '@/shared/services/apiClient'
import type {
  IShareLink,
  IShareLinkCreateRequest,
  IShareLinkListResponse,
  IShareResolveResponse,
} from '../types/shareLink.types'

/** tenantId null means an all-congregations link (admin/owner only, /share-links). */
function shareLinksUrl(tenantId: string | null): string {
  return tenantId ? `/congregations/${tenantId}/share-links` : '/share-links'
}

class ShareLinkApiService {
  async list(tenantId: string | null): Promise<IShareLink[]> {
    const response = await apiClient.get<IShareLinkListResponse>(shareLinksUrl(tenantId))
    return response.data.links
  }

  async create(tenantId: string | null, data: IShareLinkCreateRequest): Promise<IShareLink> {
    const response = await apiClient.post<IShareLink>(shareLinksUrl(tenantId), data)
    return response.data
  }

  async revoke(tenantId: string | null, linkId: string): Promise<void> {
    await apiClient.delete(`${shareLinksUrl(tenantId)}/${linkId}`)
  }

  async resolve(token: string): Promise<IShareResolveResponse> {
    const response = await apiClient.get<IShareResolveResponse>(`/share/${token}`)
    return response.data
  }
}

export const shareLinkApiService = new ShareLinkApiService()
