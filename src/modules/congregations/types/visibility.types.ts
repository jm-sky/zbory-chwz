export type VisibilityLevel = 'hidden' | 'public' | 'authenticated' | 'pastors'

export type ChurchAclRole = 'bishop' | 'regional_bishop' | 'pastor' | 'diacon'

export const VISIBILITY_LEVELS: VisibilityLevel[] = [
  'hidden',
  'public',
  'authenticated',
  'pastors',
]

export const CHURCH_ACL_ROLES: ChurchAclRole[] = [
  'bishop',
  'regional_bishop',
  'pastor',
  'diacon',
]

/** Roles the backend only lets global admins/owners grant. */
export const ELEVATED_ACL_ROLES: ChurchAclRole[] = ['bishop', 'regional_bishop']

export const DEFAULT_CARD_VISIBILITY: VisibilityLevel = 'public'
export const DEFAULT_PHONE_VISIBILITY: VisibilityLevel = 'public'
export const DEFAULT_EMAIL_VISIBILITY: VisibilityLevel = 'authenticated'
