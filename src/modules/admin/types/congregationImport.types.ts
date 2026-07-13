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

/**
 * Clergy e-mail import review queue (docs/plans/2026-07-13--clergy-email-updates.md).
 * Everything the auto-apply gate didn't clear lands here for admin review.
 */

export type TEmailImportResolution = 'own_church' | 'matched_by_name' | 'unauthorized' | 'unknown_sender' | 'ambiguous'
export type TEmailImportStatus = 'pending' | 'auto_applied' | 'approved' | 'rejected'

export interface IEmailImportInboxItem {
  message_id: string
  created_at: string
  raw_from: string
  sender_label: string | null
  resolution: TEmailImportResolution
  auth_spf: string | null
  auth_dkim: string | null
  auth_dmarc: string | null
  verification_score: number | null
  verification_reasoning: string | null
  status: TEmailImportStatus
  proposal: IImportProposal | null
}

export interface IEmailImportInboxListResponse {
  items: IEmailImportInboxItem[]
}

export interface IEmailImportApproveRequest {
  fields: IImportApplyField[]
}
