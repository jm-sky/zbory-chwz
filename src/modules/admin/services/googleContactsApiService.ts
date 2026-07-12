import { apiClient } from '@/shared/services/apiClient'
import type {
  IGoogleContactsAnalyzeRequest,
  IGoogleContactsAnalyzeResponse,
  IGoogleContactsApplyRequest,
  IGoogleContactsApplyResponse,
  IGoogleContactsAuthUrlResponse,
  IGoogleContactsConnection,
  IGoogleContactsListResponse,
} from '../types/googleContacts.types'

/**
 * API service for the admin/owner-only Google Contacts connection
 * (readonly import source — docs/plans/2026-07-10--google-contacts-sync.md).
 */
class GoogleContactsApiService {
  async getAuthUrl(): Promise<IGoogleContactsAuthUrlResponse> {
    const response = await apiClient.post<IGoogleContactsAuthUrlResponse>('/google-contacts/auth-url')
    return response.data
  }

  async completeConnection(code: string, state: string): Promise<IGoogleContactsConnection> {
    const response = await apiClient.post<IGoogleContactsConnection>('/google-contacts/callback', { code, state })
    return response.data
  }

  async getConnection(): Promise<IGoogleContactsConnection> {
    const response = await apiClient.get<IGoogleContactsConnection>('/google-contacts/connection')
    return response.data
  }

  async disconnect(): Promise<void> {
    await apiClient.delete('/google-contacts/connection')
  }

  async listContacts(): Promise<IGoogleContactsListResponse> {
    const response = await apiClient.get<IGoogleContactsListResponse>('/google-contacts/contacts')
    return response.data
  }

  async analyzeImport(request: IGoogleContactsAnalyzeRequest): Promise<IGoogleContactsAnalyzeResponse> {
    const response = await apiClient.post<IGoogleContactsAnalyzeResponse>('/google-contacts/import/analyze', request)
    return response.data
  }

  async applyImport(request: IGoogleContactsApplyRequest): Promise<IGoogleContactsApplyResponse> {
    const response = await apiClient.post<IGoogleContactsApplyResponse>('/google-contacts/import/apply', request)
    return response.data
  }
}

export const googleContactsApiService = new GoogleContactsApiService()
