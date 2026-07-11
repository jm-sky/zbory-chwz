export interface IDirectoryOption {
  id: string
  name: string
}

export interface IDirectoryFilters {
  regions: IDirectoryOption[]
  serviceTypes: IDirectoryOption[]
  groups: IDirectoryOption[]
}

export interface IDirectoryPerson {
  id: string
  firstName: string | null
  lastName: string | null
  email: string
}

export interface IDirectoryExportParams {
  regionIds: string[]
  serviceTypeIds: string[]
  groupIds: string[]
}

export interface IPersonAffiliation {
  kind: 'service' | 'group'
  label: string
  context: string | null
}

export interface IPersonBrowse {
  id: string
  firstName: string | null
  lastName: string | null
  email: string | null
  phone: string | null
  affiliations: IPersonAffiliation[]
}

export interface IPersonUpdateRequest {
  firstName?: string
  lastName?: string
  email?: string
  phone?: string
}

export interface IPersonMergeRequest {
  keepPersonId: string
  mergePersonId: string
}
