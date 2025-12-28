/**
 * Congregation (Zbór) types
 */

export interface ICongregation {
  id: string
  name: string
  description?: string
  role?: string
  createdAt: string
}

export interface ICongregationListResponse {
  congregations: ICongregation[]
}
