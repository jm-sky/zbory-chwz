import type { ChurchAclRole, VisibilityLevel } from './visibility.types'

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
  cardVisibility: string
  phoneVisibility: string
  emailVisibility: string
  sortOrder: number
  createdAt: string
  person: IPerson | null
  serviceType: IServiceType | null
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
  cardVisibility?: VisibilityLevel
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
  cardVisibility?: VisibilityLevel
  phoneVisibility?: VisibilityLevel
  emailVisibility?: VisibilityLevel
  sortOrder?: number
}
