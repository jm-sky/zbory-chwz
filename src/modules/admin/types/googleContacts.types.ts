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
  organizationName: string | null
  emailAddresses: string[]
  phoneNumbers: string[]
  notes: string | null
  suggestedType: TGoogleContactType
}

export interface IGoogleContactsListResponse {
  contacts: IGoogleContactSuggestion[]
  totalFetched: number
  matchedCount: number
}
