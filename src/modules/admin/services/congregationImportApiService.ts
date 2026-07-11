import { apiClient } from '@/shared/services/apiClient'
import type {
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
}

export const congregationImportApiService = new CongregationImportApiService()
