import type { ICongregationDetail, ICongregationDetailed } from './congregation.types'

export type ShareableVisibilityLevel = 'public' | 'authenticated'
export type ShareLinkExpiryDays = 3 | 7 | 14 | 30

export interface IShareLink {
  id: string
  token: string
  visibility_level: ShareableVisibilityLevel
  label: string | null
  expires_at: string
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

export interface IShareLinkListResponse {
  links: IShareLink[]
}

export interface IShareLinkCreateRequest {
  visibility_level: ShareableVisibilityLevel
  expires_in_days: ShareLinkExpiryDays
  label?: string
}

/** Resolution of a `/share/:token` link: one congregation, or an all-congregations list. */
export type IShareResolveResponse =
  | { kind: 'congregation', congregation: ICongregationDetail, congregations: null }
  | { kind: 'congregations', congregation: null, congregations: ICongregationDetailed[] }
