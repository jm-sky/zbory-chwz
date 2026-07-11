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
