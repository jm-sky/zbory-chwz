export type VisibilityLevel = 'hidden' | 'public' | 'authenticated' | 'pastors'

export type ChurchAclRole = 'bishop' | 'regional_bishop' | 'pastor' | 'diacon' | 'branch_responsible'

export const VISIBILITY_LEVELS: VisibilityLevel[] = [
  'hidden',
  'public',
  'authenticated',
  'pastors',
]

export const DEFAULT_PROFILE_VISIBILITY: VisibilityLevel = 'public'
export const DEFAULT_PHONE_VISIBILITY: VisibilityLevel = 'authenticated'
export const DEFAULT_EMAIL_VISIBILITY: VisibilityLevel = 'authenticated'
