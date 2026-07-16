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

export interface IPersonChangeLogEntry {
  id: string
  field: 'firstName' | 'lastName' | 'email' | 'phone'
  field_label: string
  old_value: string | null
  new_value: string | null
  source: 'admin_manual'
  actor_label: string
  created_at: string
}

export interface IPersonChangeLogResponse {
  entries: IPersonChangeLogEntry[]
}
