import { apiClient } from '@/shared/services/apiClient'

/**
 * Stats API response types
 */
export interface UserStatsResponse {
  total: number
  newThisMonth: number
}

export interface ContainerStatsResponse {
  total: number
  newThisMonth: number
}

export interface ItemStatsResponse {
  total: number
  newThisMonth: number
}

/**
 * Stats API Service
 * Handles API calls for platform statistics when backend is enabled
 */
class StatsApiService {
  /**
   * Get user statistics
   */
  async getUserStats(): Promise<UserStatsResponse> {
    const response = await apiClient.get<UserStatsResponse>('/stats/users')
    return response.data
  }

  /**
   * Get container statistics
   */
  async getContainerStats(): Promise<ContainerStatsResponse> {
    const response = await apiClient.get<ContainerStatsResponse>('/stats/containers')
    return response.data
  }

  /**
   * Get item statistics
   */
  async getItemStats(): Promise<ItemStatsResponse> {
    const response = await apiClient.get<ItemStatsResponse>('/stats/items')
    return response.data
  }

  /**
   * Get all statistics in parallel
   */
  async getAllStats(): Promise<{
    users: UserStatsResponse
    containers: ContainerStatsResponse
    items: ItemStatsResponse
  }> {
    const [users, containers, items] = await Promise.all([
      this.getUserStats(),
      this.getContainerStats(),
      this.getItemStats(),
    ])

    return { users, containers, items }
  }
}

export const statsApiService = new StatsApiService()
