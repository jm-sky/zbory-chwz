/**
 * Congregation (Zbór) types
 */

export type CongregationStatus = 'draft' | 'published' | 'published_unverified' | 'need_verification'

export interface ICongregation {
  id: string
  name: string
  description?: string
  role?: string
  status?: CongregationStatus
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

export interface IAddress {
  id: string
  tenant_id: string
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country: string
  status: string
  created_at: string
  updated_at: string
}

export interface IServiceTime {
  id: string
  tenant_id: string
  day: string
  time: string
  order: number
  created_at: string
}

export interface IContactPerson {
  id: string
  tenant_id: string
  name: string
  title?: string | null
  email?: string | null
  phone?: string | null
  order: number
  created_at: string
  updated_at: string
}

export interface ICongregationFull {
  tenant_id: string
  address: IAddress | null
  service_times: IServiceTime[]
  contact_persons: IContactPerson[]
}

export interface IAddressCreateRequest {
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country?: string
  status?: string
}

export interface IAddressUpdateRequest {
  street?: string | null
  city?: string | null
  postal_code?: string | null
  province?: string | null
  country?: string | null
  status?: string | null
}

export interface IServiceTimeCreateRequest {
  day: string
  time: string
  order?: number
}

export interface IServiceTimeUpdateRequest {
  day?: string
  time?: string
  order?: number
}

export interface IContactPersonCreateRequest {
  name: string
  title?: string | null
  email?: string | null
  phone?: string | null
  order?: number
}

export interface IContactPersonUpdateRequest {
  name?: string
  title?: string | null
  email?: string | null
  phone?: string | null
  order?: number
}
