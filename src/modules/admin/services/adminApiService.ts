import { apiClient } from '@/shared/services/apiClient'
import type {
  IAdminContainer,
  IAdminItem,
  IAdminSubscription,
  IAdminSubscriptionStats,
  IAdminUpdateSubscriptionRequest,
  IAdminUser,
} from '../types/admin.types'
import type { TUUID } from '@/shared/types/base.type'

/**
 * Admin API Service
 * Handles API calls for admin operations (users, containers, items management)
 */
class AdminApiService {
  // Users management
  async getUsers(skip = 0, limit = 100): Promise<IAdminUser[]> {
    const response = await apiClient.get<IAdminUser[]>('/admin/users', {
      params: { skip, limit },
    })
    return response.data
  }

  async getUser(id: TUUID): Promise<IAdminUser> {
    const response = await apiClient.get<IAdminUser>(`/admin/users/${id}`)
    return response.data
  }

  async updateUser(id: TUUID, data: { role?: 'user' | 'admin' | 'premium'; name?: string; email?: string; isActive?: boolean }): Promise<IAdminUser> {
    const response = await apiClient.patch<IAdminUser>(`/admin/users/${id}`, data)
    return response.data
  }

  async deleteUser(id: TUUID): Promise<void> {
    await apiClient.delete(`/admin/users/${id}`)
  }

  // Containers management
  async getContainers(skip = 0, limit = 100): Promise<IAdminContainer[]> {
    const response = await apiClient.get<IAdminContainer[]>('/admin/containers', {
      params: { skip, limit },
    })
    return response.data
  }

  async getContainer(id: TUUID): Promise<IAdminContainer> {
    const response = await apiClient.get<IAdminContainer>(`/admin/containers/${id}`)
    return response.data
  }

  async updateContainer(id: TUUID, data: { isPublic?: boolean }): Promise<IAdminContainer> {
    const response = await apiClient.patch<IAdminContainer>(`/admin/containers/${id}`, data)
    return response.data
  }

  async deleteContainer(id: TUUID): Promise<void> {
    await apiClient.delete(`/admin/containers/${id}`)
  }

  // Items management
  async getItems(skip = 0, limit = 100): Promise<IAdminItem[]> {
    const response = await apiClient.get<IAdminItem[]>('/admin/items', {
      params: { skip, limit },
    })
    return response.data
  }

  async getItem(id: TUUID): Promise<IAdminItem> {
    const response = await apiClient.get<IAdminItem>(`/admin/items/${id}`)
    return response.data
  }

  async deleteItem(id: TUUID): Promise<void> {
    await apiClient.delete(`/admin/items/${id}`)
  }

  // Content reports management - REMOVED (gear module dependency)
  // async getReports(params: {
  //   status?: ReportStatus
  //   containerId?: TUUID
  //   limit?: number
  //   offset?: number
  // }): Promise<IContentReportListResponse> {
  //   const response = await apiClient.get<IContentReportListResponse>('/admin/reports', {
  //     params,
  //   })
  //   return response.data
  // }

  // async updateReportStatus(reportId: TUUID, data: IUpdateReportRequest): Promise<IContentReport> {
  //   const response = await apiClient.patch<IContentReport>(`/admin/reports/${reportId}`, data)
  //   return response.data
  // }

  // Subscriptions management
  async getSubscriptions(skip = 0, limit = 100): Promise<IAdminSubscription[]> {
    const response = await apiClient.get<IAdminSubscription[]>('/billing/admin/subscriptions', {
      params: { skip, limit },
    })
    return response.data
  }

  async getSubscriptionStats(): Promise<IAdminSubscriptionStats> {
    const response = await apiClient.get<IAdminSubscriptionStats>('/billing/admin/subscriptions/stats')
    return response.data
  }

  async updateSubscription(subscriptionId: TUUID, data: IAdminUpdateSubscriptionRequest): Promise<IAdminSubscription> {
    const response = await apiClient.patch<IAdminSubscription>(`/billing/admin/subscriptions/${subscriptionId}`, data)
    return response.data
  }

  async cancelSubscription(subscriptionId: TUUID, reason?: string): Promise<IAdminSubscription> {
    const response = await apiClient.post<IAdminSubscription>(`/billing/admin/subscriptions/${subscriptionId}/cancel`, {
      reason,
    })
    return response.data
  }
}

export const adminApiService = new AdminApiService()
