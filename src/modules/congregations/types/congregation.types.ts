/**
 * Congregation (Zbór) types
 */
import type { VisibilityLevel } from './visibility.types'

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
  website?: string | null
  email?: string | null
  iban?: string | null
  latitude?: number | null
  longitude?: number | null
  // Service times
  service_times?: Array<{ day: string; time: string; description?: string | null }>
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
  description?: string | null
  // Visibility levels for this contact's fields; only present for viewers who can manage the congregation.
  profile_visibility?: VisibilityLevel | null
  phone_visibility?: VisibilityLevel | null
  email_visibility?: VisibilityLevel | null
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
  website?: string | null
  email?: string | null
  iban?: string | null
  latitude?: number | null
  longitude?: number | null
  // Full, unlimited service times
  service_times: Array<{ day: string; time: string; description?: string | null }>
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

export type GeocodeStatus = 'pending' | 'manual'

export interface IAddress {
  id: string
  tenant_id: string
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country: string
  website?: string | null
  email?: string | null
  iban?: string | null
  latitude?: number | null
  longitude?: number | null
  geocode_status?: GeocodeStatus
  status: string
  created_at: string
  updated_at: string
  last_updated_at?: string | null
  last_updated_label?: string | null
}

export interface IServiceTime {
  id: string
  tenant_id: string
  day: string
  time: string
  description?: string | null
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
  website?: string | null
  email?: string | null
  iban?: string | null
  latitude?: number | null
  longitude?: number | null
  status?: string
}

export interface IAddressUpdateRequest {
  street?: string | null
  city?: string | null
  postal_code?: string | null
  province?: string | null
  country?: string | null
  website?: string | null
  email?: string | null
  iban?: string | null
  latitude?: number | null
  longitude?: number | null
  status?: string | null
}

export interface IGeocodeRequest {
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country?: string
}

export interface IGeocodeResponse {
  latitude?: number | null
  longitude?: number | null
  display_name?: string | null
  confidence: 'exact' | 'approximate' | 'not_found'
}

export interface IServiceTimeCreateRequest {
  day: string
  time: string
  description?: string | null
  order?: number
}

export interface IServiceTimeUpdateRequest {
  day?: string
  time?: string
  description?: string | null
  order?: number
}

/** Field-level change history (docs/plans/2026-07-13--clergy-email-updates.md). */
export interface IChangeLogEntry {
  id: string
  section: 'address' | 'contact'
  field: string
  field_label: string
  old_value: string | null
  new_value: string | null
  source: 'admin_manual' | 'import_paste' | 'email_auto' | 'email_reviewed'
  actor_label: string
  created_at: string
}

export interface IChangeLogResponse {
  entries: IChangeLogEntry[]
}
