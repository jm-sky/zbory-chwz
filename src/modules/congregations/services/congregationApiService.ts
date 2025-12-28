import { apiClient } from '@/shared/services/apiClient'
import type {
  CongregationStatus,
  IAddress,
  IAddressCreateRequest,
  IAddressUpdateRequest,
  ICongregation,
  ICongregationDetailed,
  ICongregationDetailedListResponse,
  ICongregationFull,
  IContactPerson,
  IContactPersonCreateRequest,
  IContactPersonUpdateRequest,
  IServiceTime,
  IServiceTimeCreateRequest,
  IServiceTimeUpdateRequest,
} from '../types/congregation.types'

interface IAdminTenant {
  id: string
  name: string
  description?: string
  status?: string
  createdAt: string
}

export interface IUpdateCongregationRequest {
  name?: string
  description?: string
  status?: string
}

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

  /**
   * Get detailed list of congregations with address, service times, and contact info (public endpoint)
   */
  async getCongregationsDetailed(): Promise<ICongregationDetailed[]> {
    try {
      const response = await apiClient.get<ICongregationDetailedListResponse>(
        '/congregations/detailed',
      )
      return response.data.congregations
    } catch (error) {
      console.warn('Failed to fetch detailed congregations:', error)
      // Fallback to basic list
      return this.getCongregations()
    }
  }

  /**
   * Update congregation (requires tenant membership or admin/owner role)
   */
  async updateCongregation(id: string, data: IUpdateCongregationRequest): Promise<void> {
    await apiClient.patch(`/admin/tenants/${id}`, data)
  }

  /**
   * Unpublish congregation (set status to draft)
   */
  async unpublishCongregation(id: string): Promise<void> {
    await this.updateCongregation(id, { status: 'draft' })
  }

  /**
   * Get full congregation data including address, service times, and contact persons
   */
  async getCongregationFull(id: string): Promise<ICongregationFull> {
    const response = await apiClient.get<ICongregationFull>(`/congregations/${id}/full`)
    return response.data
  }

  /**
   * Get tenant basic info (name, description, status)
   */
  async getTenant(id: string): Promise<ICongregation> {
    // Try to get from /tenants first (for tenant users)
    try {
      const response = await apiClient.get<TenantListResponse>('/tenants')
      const tenant = response.data.tenants.find(t => t.id === id)
      if (tenant) {
        // /tenants endpoint doesn't return status, so we need to get it from admin endpoint
        // But for now, default to draft if not found
        return {
          id: tenant.id,
          name: tenant.name,
          description: tenant.description,
          role: tenant.role || undefined,
          status: 'draft' as CongregationStatus,
          createdAt: tenant.createdAt,
        }
      }
    } catch {
      // Fallback to admin endpoint
    }
    
    // Fallback to admin endpoint (for admin/owner users)
    try {
      const adminResponse = await apiClient.get<{ tenants: IAdminTenant[] }>('/admin/tenants')
      const tenant = adminResponse.data.tenants.find(t => t.id === id)
      if (tenant) {
        return {
          id: tenant.id,
          name: tenant.name,
          description: tenant.description,
          status: (tenant.status || 'draft') as CongregationStatus,
          createdAt: tenant.createdAt,
        }
      }
    } catch {
      // If admin endpoint also fails, throw error
    }
    
    throw new Error('Tenant not found')
  }

  /**
   * Get address for a congregation
   */
  async getAddress(tenantId: string): Promise<IAddress | null> {
    try {
      const response = await apiClient.get<IAddress>(`/congregations/${tenantId}/address`)
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  /**
   * Create or update address for a congregation
   */
  async createOrUpdateAddress(tenantId: string, data: IAddressCreateRequest): Promise<IAddress> {
    const response = await apiClient.post<IAddress>(`/congregations/${tenantId}/address`, data)
    return response.data
  }

  /**
   * Update address for a congregation
   */
  async updateAddress(tenantId: string, data: IAddressUpdateRequest): Promise<IAddress> {
    const response = await apiClient.patch<IAddress>(`/congregations/${tenantId}/address`, data)
    return response.data
  }

  /**
   * Get service times for a congregation
   */
  async getServiceTimes(tenantId: string): Promise<IServiceTime[]> {
    const response = await apiClient.get<IServiceTime[]>(`/congregations/${tenantId}/service-times`)
    return response.data
  }

  /**
   * Create service time for a congregation
   */
  async createServiceTime(tenantId: string, data: IServiceTimeCreateRequest): Promise<IServiceTime> {
    const response = await apiClient.post<IServiceTime>(`/congregations/${tenantId}/service-times`, data)
    return response.data
  }

  /**
   * Update service time for a congregation
   */
  async updateServiceTime(tenantId: string, serviceTimeId: string, data: IServiceTimeUpdateRequest): Promise<IServiceTime> {
    const response = await apiClient.patch<IServiceTime>(`/congregations/${tenantId}/service-times/${serviceTimeId}`, data)
    return response.data
  }

  /**
   * Delete service time for a congregation
   */
  async deleteServiceTime(tenantId: string, serviceTimeId: string): Promise<void> {
    await apiClient.delete(`/congregations/${tenantId}/service-times/${serviceTimeId}`)
  }

  /**
   * Get contact persons for a congregation
   */
  async getContactPersons(tenantId: string): Promise<IContactPerson[]> {
    const response = await apiClient.get<IContactPerson[]>(`/congregations/${tenantId}/contact-persons`)
    return response.data
  }

  /**
   * Create contact person for a congregation
   */
  async createContactPerson(tenantId: string, data: IContactPersonCreateRequest): Promise<IContactPerson> {
    const response = await apiClient.post<IContactPerson>(`/congregations/${tenantId}/contact-persons`, data)
    return response.data
  }

  /**
   * Update contact person for a congregation
   */
  async updateContactPerson(tenantId: string, contactPersonId: string, data: IContactPersonUpdateRequest): Promise<IContactPerson> {
    const response = await apiClient.patch<IContactPerson>(`/congregations/${tenantId}/contact-persons/${contactPersonId}`, data)
    return response.data
  }

  /**
   * Delete contact person for a congregation
   */
  async deleteContactPerson(tenantId: string, contactPersonId: string): Promise<void> {
    await apiClient.delete(`/congregations/${tenantId}/contact-persons/${contactPersonId}`)
  }
}

export const congregationApiService = new CongregationApiService()
