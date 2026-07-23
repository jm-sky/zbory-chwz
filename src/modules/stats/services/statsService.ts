import { useBackend } from '@/shared/composables/useBackend'
import { statsApiService } from './statsApiService'
import { statsLocalService } from './statsLocalService'

/**
 * Stats Service Factory
 *
 * Returns appropriate service based on backend status.
 * When backend is enabled, uses API service.
 * Otherwise, uses localStorage service.
 *
 * Note: Stats endpoints are public and don't require authentication,
 * but we still check backend.enabled to decide which service to use.
 */
export const statsService = () => {
  const { isBackendEnabled } = useBackend()

  if (isBackendEnabled.value) {
    // Use API service when backend is enabled
    return {
      async getUserStats() {
        try {
          return await statsApiService.getUserStats()
        } catch (error) {
          // Fallback to local service on API error
          console.warn('API failed, falling back to local service', error)
          return statsLocalService.getUserStats()
        }
      },
      async getContainerStats() {
        try {
          return await statsApiService.getContainerStats()
        } catch (error) {
          // Fallback to local service on API error
          console.warn('API failed, falling back to local service', error)
          return statsLocalService.getContainerStats()
        }
      },
      async getItemStats() {
        try {
          return await statsApiService.getItemStats()
        } catch (error) {
          // Fallback to local service on API error
          console.warn('API failed, falling back to local service', error)
          return statsLocalService.getItemStats()
        }
      },
      async getAllStats() {
        try {
          return await statsApiService.getAllStats()
        } catch (error) {
          // Fallback to local service on API error
          console.warn('API failed, falling back to local service', error)
          return statsLocalService.getAllStats()
        }
      },
    }
  }

  // Offline mode - use localStorage service
  return statsLocalService
}
