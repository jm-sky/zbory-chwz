/**
 * Types for the Google Contacts (People API) connection — Phase 1
 * (docs/plans/2026-07-10--google-contacts-sync.md): connect (readonly),
 * connection status, and the "zbór"/"chwz" filtered contact list.
 */

export type TGoogleContactsScope = 'readonly' | 'readonly_write'
export type TGoogleContactType = 'church' | 'person'

export interface IGoogleContactsAuthUrlResponse {
  authUrl: string
  state: string
}

export interface IGoogleContactsConnection {
  connected: boolean
  scope: TGoogleContactsScope | null
  connectedAt: string | null
  expiresAt: string | null
}

export interface IGoogleContactSuggestion {
  resourceName: string
  displayName: string | null
  firstName: string | null
  lastName: string | null
  organizationName: string | null
  emailAddresses: string[]
  phoneNumbers: string[]
  notes: string | null
  suggestedType: TGoogleContactType
  addressStreet: string | null
  addressCity: string | null
  addressPostalCode: string | null
  addressProvince: string | null
  addressCountry: string | null
}

export interface IGoogleContactsListResponse {
  contacts: IGoogleContactSuggestion[]
  totalFetched: number
  matchedCount: number
}

// Phase 2/3 — mapping screen (classify/match) and import to the database.

export interface IGoogleContactImportSelection {
  contact: IGoogleContactSuggestion
  type: TGoogleContactType
}

export interface IGoogleContactsAnalyzeRequest {
  items: IGoogleContactImportSelection[]
}

export type TGoogleContactMatchType = 'matched' | 'new'

export type TGoogleContactFieldGroup = 'address' | 'contact'

export interface IGoogleContactFieldChange {
  field: string
  label: string
  group: TGoogleContactFieldGroup
  oldValue: string | null
  newValue: string | null
}

export interface IGoogleContactChurchProposal {
  resourceName: string
  matchType: TGoogleContactMatchType
  tenantId: string | null
  matchedName: string | null
  confidence: number
  name: string
  street: string | null
  city: string | null
  postalCode: string | null
  province: string | null
  country: string | null
  phone: string | null
  email: string | null
  fields: IGoogleContactFieldChange[]
}

export interface IGoogleContactPersonProposal {
  resourceName: string
  matchType: TGoogleContactMatchType
  personId: string | null
  matchedName: string | null
  matchedBy: 'email' | 'phone' | null
  firstName: string | null
  lastName: string | null
  email: string | null
  phone: string | null
  fields: IGoogleContactFieldChange[]
}

export interface IGoogleContactChurchFieldDiffRequest {
  tenantId: string | null
  street: string | null
  city: string | null
  postalCode: string | null
  province: string | null
  country: string | null
  phone: string | null
  email: string | null
}

export interface IGoogleContactChurchFieldDiffResponse {
  fields: IGoogleContactFieldChange[]
}

export interface IGoogleContactsCandidateTenant {
  tenantId: string
  name: string
}

export interface IGoogleContactsServiceType {
  id: string
  name: string
}

export interface IGoogleContactsAnalyzeResponse {
  churchProposals: IGoogleContactChurchProposal[]
  personProposals: IGoogleContactPersonProposal[]
  candidateTenants: IGoogleContactsCandidateTenant[]
  serviceTypes: IGoogleContactsServiceType[]
}

export type TGoogleContactApplyAction = 'create' | 'update' | 'skip'

export interface IGoogleContactChurchApplyItem {
  resourceName: string
  action: TGoogleContactApplyAction
  tenantId?: string | null
  name?: string | null
  street?: string | null
  city?: string | null
  postalCode?: string | null
  province?: string | null
  country?: string | null
  phone?: string | null
  email?: string | null
}

export interface IGoogleContactPersonApplyItem {
  resourceName: string
  action: TGoogleContactApplyAction
  personId?: string | null
  firstName?: string | null
  lastName?: string | null
  email?: string | null
  phone?: string | null
  assignToChurch: boolean
  churchId?: string | null
  // Set instead of churchId when assigning to a church that's also being
  // created in this same batch — matches that church proposal's resourceName.
  newChurchResourceName?: string | null
  serviceTypeId?: string | null
  customServiceName?: string | null
}

export interface IGoogleContactsApplyRequest {
  churchItems: IGoogleContactChurchApplyItem[]
  personItems: IGoogleContactPersonApplyItem[]
}

export interface IGoogleContactsApplyResponse {
  churchesCreated: number
  churchesUpdated: number
  personsCreated: number
  personsUpdated: number
  skipped: number
}
