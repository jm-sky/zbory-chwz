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

export interface ICongregationDetailed extends ICongregation {
  // Address info
  city?: string | null
  street?: string | null
  postal_code?: string | null
  // Service times
  service_times?: Array<{ day: string; time: string }>
  // Contact person
  contact_name?: string | null
  contact_title?: string | null
  contact_phone?: string | null
  contact_email?: string | null
}

export interface ICongregationListResponse {
  congregations: ICongregation[]
}

export interface ICongregationDetailedListResponse {
  congregations: ICongregationDetailed[]
}
