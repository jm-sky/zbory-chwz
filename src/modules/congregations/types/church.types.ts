import type { ChurchAclRole, VisibilityLevel } from './visibility.types'

export interface IGrantableRole {
  name: ChurchAclRole
  scopeType: string
  permissions: string[]
}

export type AccountStatus = 'none' | 'invited' | 'expired' | 'active'

export interface IAccountState {
  userId: string
  status: AccountStatus
  invitedAt: string | null
  invitationExpiresAt: string | null
}

export interface IInviteResponse {
  invitedAt: string
  invitationExpiresAt: string
}

export interface IServiceType {
  id: string
  slug: string
  name: string
  scopeType: string
  suggestedRole: string | null
  isSeniorTier: boolean
  sortOrder: number
}

export interface IPerson {
  id: string
  firstName: string | null
  lastName: string | null
  email: string | null
  phone: string | null
  userId: string | null
}

export interface IBranch {
  id: string
  churchId: string
  name: string
  slug: string
  visibility: string
  createdAt: string
}

export interface IServiceAssignment {
  id: string
  personId: string
  serviceTypeId: string | null
  customServiceName: string | null
  description: string | null
  scopeType: string
  scopeId: string
  showOnList: boolean
  profileVisibility: string
  phoneVisibility: string
  emailVisibility: string
  sortOrder: number
  createdAt: string
  person: IPerson | null
  serviceType: IServiceType | null
  account: IAccountState | null
}

export interface IBranchCreateRequest {
  name: string
  slug?: string
  visibility?: string
}

export interface IServiceAssignmentCreateRequest {
  personId?: string
  firstName?: string
  lastName?: string
  email?: string
  phone?: string
  serviceTypeId?: string
  customServiceName?: string
  description?: string
  createAccount?: boolean
  suggestedRole?: ChurchAclRole
  showOnList?: boolean
  profileVisibility?: VisibilityLevel
  phoneVisibility?: VisibilityLevel
  emailVisibility?: VisibilityLevel
  sortOrder?: number
}

export interface IServiceAssignmentUpdateRequest {
  serviceTypeId?: string
  customServiceName?: string
  description?: string
  firstName?: string
  lastName?: string
  email?: string
  phone?: string
  showOnList?: boolean
  profileVisibility?: VisibilityLevel
  phoneVisibility?: VisibilityLevel
  emailVisibility?: VisibilityLevel
  sortOrder?: number
}
