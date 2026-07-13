import { apiClient } from '@/shared/services/apiClient'
import type {
  IEmailImportApproveRequest,
  IEmailImportInboxListResponse,
  IImportAnalyzeResponse,
  IImportApplyRequest,
  IImportApplyResponse,
} from '../types/congregationImport.types'

/**
 * API service for the AI-assisted congregation address/contact import.
 */
class CongregationImportApiService {
  async analyze(rawText: string): Promise<IImportAnalyzeResponse> {
    const response = await apiClient.post<IImportAnalyzeResponse>(
      '/admin/congregations/import/analyze',
      { raw_text: rawText },
    )
    return response.data
  }

  async apply(request: IImportApplyRequest): Promise<IImportApplyResponse> {
    const response = await apiClient.post<IImportApplyResponse>(
      '/admin/congregations/import/apply',
      request,
    )
    return response.data
  }

  async listInbox(): Promise<IEmailImportInboxListResponse> {
    const response = await apiClient.get<IEmailImportInboxListResponse>(
      '/admin/congregations/import/inbox',
    )
    return response.data
  }

  async approveInboxItem(messageId: string, request: IEmailImportApproveRequest): Promise<IImportApplyResponse> {
    const response = await apiClient.post<IImportApplyResponse>(
      `/admin/congregations/import/inbox/${messageId}/approve`,
      request,
    )
    return response.data
  }

  async rejectInboxItem(messageId: string): Promise<void> {
    await apiClient.post(`/admin/congregations/import/inbox/${messageId}/reject`)
  }
}

export const congregationImportApiService = new CongregationImportApiService()
