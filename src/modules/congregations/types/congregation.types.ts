/**
 * Congregation (Zbór) types
 */

export type CongregationStatus = 'draft' | 'published' | 'published_unverified' | 'need_verification'

/** A congregation, or a placówka (branch) belonging to one. */
export type CongregationType = 'church' | 'branch'

export interface ICongregation {
  id: string
  name: string
  description?: string
  role?: string
  status?: CongregationStatus
  createdAt: string
}

export interface ICongregationDetailed extends ICongregation {
  type?: CongregationType
  parent_id?: string | null
  parent_name?: string | null
  // Address info
  city?: string | null
  street?: string | null
  postal_code?: string | null
  province?: string | null
  /** ISO 3166-1 alpha-2 country code, e.g. 'PL' */
  country?: string | null
  // Service times
  service_times?: Array<{ day: string; time: string }>
  // Contacts from public service assignments
  card_contacts?: ICardContact[]
  // Legacy single contact (first card_contacts entry)
  contact_name?: string | null
  contact_title?: string | null
  contact_phone?: string | null
  contact_email?: string | null
}

export interface ICardContact {
  name?: string | null
  title?: string | null
  phone?: string | null
  email?: string | null
}

export interface ICongregationBranchSummary {
  id: string
  name: string
}

/** Full congregation detail, with fields already filtered server-side by the viewer's visibility level. */
export interface ICongregationDetail {
  id: string
  name: string
  description?: string | null
  status?: CongregationStatus
  createdAt: string
  city?: string | null
  street?: string | null
  postal_code?: string | null
  province?: string | null
  /** ISO 3166-1 alpha-2 country code, e.g. 'PL' */
  country?: string | null
  // Full, unlimited service times
  service_times: Array<{ day: string; time: string }>
  // Visible profile contacts, filtered by viewer's visibility level
  card_contacts: ICardContact[]
  // Hidden profile contacts; only present when canManage is true
  hidden_contacts?: ICardContact[]
  // Publicly visible branches (placówki)
  branches: ICongregationBranchSummary[]
  /** The viewer's membership role in this congregation, if any */
  role?: string | null
  /** Whether the viewer may edit this congregation (member or global admin/owner) */
  canManage: boolean
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

export interface ICongregationFull {
  tenant_id: string
  address: IAddress | null
  service_times: IServiceTime[]
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
