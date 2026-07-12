/**
 * Types for the AI-assisted congregation address/contact import
 * (paste free-text notes -> review a field diff -> apply).
 */

export type TImportFieldKey =
  | 'street'
  | 'city'
  | 'postal_code'
  | 'province'
  | 'country'
  | 'contact_name'
  | 'contact_title'
  | 'contact_phone'
  | 'contact_email'

export type TImportFieldGroup = 'address' | 'contact'

export interface IImportFieldChange {
  field: TImportFieldKey
  label: string
  group: TImportFieldGroup
  old_value: string | null
  new_value: string | null
}

export interface IImportCandidateTenant {
  tenant_id: string
  name: string
}

export interface IImportProposal {
  proposal_id: string
  detected_name: string
  match_type: 'matched' | 'new'
  tenant_id: string | null
  matched_name: string | null
  confidence: number
  contact_context: string | null
  contact_person_id: string | null
  fields: IImportFieldChange[]
}

export interface IImportAnalyzeRequest {
  raw_text: string
}

export interface IImportAnalyzeResponse {
  proposals: IImportProposal[]
  candidates: IImportCandidateTenant[]
}

export interface IImportApplyField {
  field: TImportFieldKey
  value: string | null
  apply: boolean
}

export interface IImportApplyItem {
  action: 'update' | 'create' | 'skip'
  tenant_id?: string | null
  congregation_name?: string | null
  contact_person_id?: string | null
  fields: IImportApplyField[]
}

export interface IImportApplyRequest {
  items: IImportApplyItem[]
}

export interface IImportApplyResponse {
  created: number
  updated: number
  skipped: number
}
