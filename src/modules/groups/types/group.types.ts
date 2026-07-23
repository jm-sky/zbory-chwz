export type GroupVisibility = 'public' | 'authenticated' | 'private'
export type GroupScopeType = 'community' | 'region' | 'global'

export interface IGroupPerson {
  id: string
  firstName: string | null
  lastName: string | null
  email: string | null
  phone: string | null
}

export interface IGroupMembership {
  id: string
  groupId: string
  personId: string
  roleLabel: string | null
  joinedAt: string
  leftAt: string | null
  person: IGroupPerson | null
}

export interface IGroup {
  id: string
  name: string
  slug: string
  description: string | null
  scopeType: GroupScopeType
  scopeId: string | null
  visibility: GroupVisibility
  stewardUserId: string | null
  createdAt: string
  updatedAt: string
  memberCount: number
}

export interface IGroupDetail extends IGroup {
  memberships: IGroupMembership[]
}

export interface IGroupCreateRequest {
  name: string
  slug?: string
  description?: string
  scopeType?: GroupScopeType
  scopeId?: string
  visibility?: GroupVisibility
  stewardUserId?: string
}

export interface IGroupUpdateRequest {
  name?: string
  slug?: string
  description?: string
  scopeType?: GroupScopeType
  scopeId?: string
  visibility?: GroupVisibility
  stewardUserId?: string
}

export interface IGroupMembershipCreateRequest {
  personId?: string
  firstName?: string
  lastName?: string
  email?: string
  phone?: string
  roleLabel?: string
}

export interface IGroupMembershipUpdateRequest {
  roleLabel?: string
}
