import { describe, expect, it } from 'vitest'
import { inheritedPermissions, isWideScope, permissionCatalog } from './permissionState'
import type { IGrantableRole } from '@/modules/congregations/types/church.types'

function role(name: string, permissions: string[]): IGrantableRole {
  return { name: name as IGrantableRole['name'], scopeType: 'church', permissions }
}

describe('isWideScope', () => {
  it('is true for community and region — deny there is global in the chain (§2)', () => {
    expect(isWideScope('community')).toBe(true)
    expect(isWideScope('region')).toBe(true)
  })

  it('is false for church and branch', () => {
    expect(isWideScope('church')).toBe(false)
    expect(isWideScope('branch')).toBe(false)
  })
})

describe('permissionCatalog', () => {
  it('deduplicates and sorts permissions across every role', () => {
    const roles = [
      role('pastor', ['church.edit', 'people.manage']),
      role('diacon', ['church.edit', 'events.manage']),
    ]
    expect(permissionCatalog(roles)).toEqual(['church.edit', 'events.manage', 'people.manage'])
  })

  it('is empty when there are no roles', () => {
    expect(permissionCatalog([])).toEqual([])
  })
})

describe('inheritedPermissions', () => {
  const roles = [
    role('pastor', ['church.edit', 'church.publish']),
    role('diacon', ['church.edit', 'people.manage']),
  ]

  it('unions permissions from every held role', () => {
    const result = inheritedPermissions(roles, ['pastor', 'diacon'])
    expect(result).toEqual(new Set(['church.edit', 'church.publish', 'people.manage']))
  })

  it('is empty when the user holds none of the catalog roles', () => {
    expect(inheritedPermissions(roles, [])).toEqual(new Set())
  })

  it('ignores role names not present in the catalog', () => {
    expect(inheritedPermissions(roles, ['bishop'])).toEqual(new Set())
  })
})
