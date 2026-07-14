import { apiClient } from '@/shared/services/apiClient'
import type { ICongregationDetail } from '../types/congregation.types'
import type {
  IShareLink,
  IShareLinkCreateRequest,
  IShareLinkListResponse,
} from '../types/shareLink.types'

class ShareLinkApiService {
  async list(tenantId: string): Promise<IShareLink[]> {
    const response = await apiClient.get<IShareLinkListResponse>(`/congregations/${tenantId}/share-links`)
    return response.data.links
  }

  async create(tenantId: string, data: IShareLinkCreateRequest): Promise<IShareLink> {
    const response = await apiClient.post<IShareLink>(`/congregations/${tenantId}/share-links`, data)
    return response.data
  }

  async revoke(tenantId: string, linkId: string): Promise<void> {
    await apiClient.delete(`/congregations/${tenantId}/share-links/${linkId}`)
  }

  async getSharedCongregation(token: string): Promise<ICongregationDetail> {
    const response = await apiClient.get<ICongregationDetail>(`/share/${token}`)
    return response.data
  }
}

export const shareLinkApiService = new ShareLinkApiService()
