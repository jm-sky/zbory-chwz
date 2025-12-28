import { apiClient } from '@/shared/services/apiClient'
import type { ICongregation } from '../types/congregation.types'

/**
 * Backend API response type
 */
interface TenantResponse {
  id: string
  name: string
  description?: string
  role: string
  createdAt: string
}

interface TenantListResponse {
  tenants: TenantResponse[]
}

/**
 * Congregation API Service
 * Handles API calls for congregations (public list)
 */
class CongregationApiService {
  /**
   * Get list of congregations (public endpoint)
   */
  async getCongregations(): Promise<ICongregation[]> {
    try {
      const response = await apiClient.get<TenantListResponse>('/congregations')
      return response.data.tenants.map((tenant) => ({
        id: tenant.id,
        name: tenant.name,
        description: tenant.description,
        role: tenant.role || undefined,
        createdAt: tenant.createdAt,
      }))
    } catch (error) {
      // If /congregations doesn't exist, try /tenants (which requires auth)
      // This is a fallback for backward compatibility
      try {
        const response = await apiClient.get<TenantListResponse>('/tenants')
        return response.data.tenants.map((tenant) => ({
          id: tenant.id,
          name: tenant.name,
          description: tenant.description,
          role: tenant.role || undefined,
          createdAt: tenant.createdAt,
        }))
      } catch {
        // If both fail, return empty array
        console.warn('Failed to fetch congregations:', error)
        return []
      }
    }
  }
}

export const congregationApiService = new CongregationApiService()
