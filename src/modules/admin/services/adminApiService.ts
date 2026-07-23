import { isAxiosError } from 'axios'
import { apiClient } from '@/shared/services/apiClient'
import type { IAdminUser } from '../types/admin.types'
import type {
  IAddress,
  IAddressCreateRequest,
  IAddressUpdateRequest,
  IAdminTenant,
  IAdminTenantMembership,
  ICreateTenantMembershipRequest,
  ICreateTenantRequest,
  IUpdateTenantMembershipRequest,
  IUpdateTenantRequest,
} from '../types/tenant.types'
import type { TUUID } from '@/shared/types/base.type'

/**
 * Admin API Service
 * Handles API calls for admin operations (users and tenants management)
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

  // Tenants/Congregations management
  async getTenants(includeDeleted = false): Promise<IAdminTenant[]> {
    const response = await apiClient.get<{ tenants: IAdminTenant[] }>('/admin/tenants', {
      params: { include_deleted: includeDeleted },
    })
    return response.data.tenants
  }

  async createTenant(data: ICreateTenantRequest): Promise<IAdminTenant> {
    const response = await apiClient.post<IAdminTenant>('/admin/tenants', data)
    return response.data
  }

  async updateTenant(id: string, data: IUpdateTenantRequest): Promise<IAdminTenant> {
    const response = await apiClient.patch<IAdminTenant>(`/admin/tenants/${id}`, data)
    return response.data
  }

  /** Soft delete — the congregation keeps its data and can be restored. */
  async deleteTenant(id: string): Promise<void> {
    await apiClient.delete(`/admin/tenants/${id}`)
  }

  async restoreTenant(id: string): Promise<IAdminTenant> {
    const response = await apiClient.post<IAdminTenant>(`/admin/tenants/${id}/restore`)
    return response.data
  }

  // Tenant Memberships management
  async getTenantMemberships(tenantId: string): Promise<IAdminTenantMembership[]> {
    const response = await apiClient.get<IAdminTenantMembership[]>(`/admin/tenants/${tenantId}/memberships`)
    return response.data
  }

  async createTenantMembership(tenantId: string, data: ICreateTenantMembershipRequest): Promise<IAdminTenantMembership> {
    const response = await apiClient.post<IAdminTenantMembership>(`/admin/tenants/${tenantId}/memberships`, data)
    return response.data
  }

  async updateTenantMembership(tenantId: string, userId: string, data: IUpdateTenantMembershipRequest): Promise<IAdminTenantMembership> {
    const response = await apiClient.patch<IAdminTenantMembership>(`/admin/tenants/${tenantId}/memberships/${userId}`, data)
    return response.data
  }

  async deleteTenantMembership(tenantId: string, userId: string): Promise<void> {
    await apiClient.delete(`/admin/tenants/${tenantId}/memberships/${userId}`)
  }

  // Address management
  async getAddress(tenantId: string): Promise<IAddress | null> {
    try {
      const response = await apiClient.get<IAddress>(`/congregations/${tenantId}/address`)
      return response.data
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  async createOrUpdateAddress(tenantId: string, data: IAddressCreateRequest): Promise<IAddress> {
    const response = await apiClient.post<IAddress>(`/congregations/${tenantId}/address`, data)
    return response.data
  }

  async updateAddress(tenantId: string, data: IAddressUpdateRequest): Promise<IAddress> {
    const response = await apiClient.patch<IAddress>(`/congregations/${tenantId}/address`, data)
    return response.data
  }
}

export const adminApiService = new AdminApiService()
