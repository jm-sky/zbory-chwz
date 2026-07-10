import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'
import type { ICongregationDetailed } from '../types/congregation.types'
import { ANY_VALUE, useCongregationFilters } from './useCongregationFilters'

function congregation(overrides: Partial<ICongregationDetailed>): ICongregationDetailed {
  return {
    id: Math.random().toString(36).slice(2),
    name: 'Zbór',
    createdAt: '2026-01-01T00:00:00Z',
    type: 'church',
    country: 'PL',
    ...overrides,
  }
}

const wroclaw = congregation({
  name: 'ZBÓR WE WROCŁAWIU',
  city: 'Wrocław',
  province: 'dolnoslaskie',
})
const warszawa = congregation({
  name: 'ZBÓR W WARSZAWIE',
  city: 'Warszawa',
  province: 'mazowieckie',
})
const marktredwitz = congregation({
  name: 'ZBÓR W MARKTREDWITZ',
  city: 'Marktredwitz',
  country: 'DE',
  province: null,
})
const branch = congregation({
  name: 'Placówka Psie Pole',
  type: 'branch',
  parent_name: 'ZBÓR WE WROCŁAWIU',
  city: 'Wrocław',
  province: 'dolnoslaskie',
})

const all = [wroclaw, warszawa, marktredwitz, branch]

describe('useCongregationFilters', () => {
  it('returns everything by default', () => {
    const filters = useCongregationFilters(ref(all))
    expect(filters.filtered.value).toHaveLength(4)
    expect(filters.isFiltered.value).toBe(false)
  })

  it('tolerates undefined data while the query loads', () => {
    const filters = useCongregationFilters(ref(undefined))
    expect(filters.filtered.value).toEqual([])
    expect(filters.availableCountries.value).toEqual([])
  })

  it('offers only the countries and provinces present in the data', () => {
    const filters = useCongregationFilters(ref(all))
    expect(filters.availableCountries.value).toEqual(['DE', 'PL'])
    expect(filters.availableProvinces.value).toEqual(['dolnoslaskie', 'mazowieckie'])
  })

  it('narrows provinces to the selected country', () => {
    const filters = useCongregationFilters(ref(all))
    filters.country.value = 'DE'
    expect(filters.availableProvinces.value).toEqual([])
  })

  it('filters by country', () => {
    const filters = useCongregationFilters(ref(all))
    filters.country.value = 'DE'
    expect(filters.filtered.value.map((c) => c.name)).toEqual(['ZBÓR W MARKTREDWITZ'])
  })

  it('filters by province', () => {
    const filters = useCongregationFilters(ref(all))
    filters.province.value = 'mazowieckie'
    expect(filters.filtered.value.map((c) => c.name)).toEqual(['ZBÓR W WARSZAWIE'])
  })

  it('hides branches on request', () => {
    const filters = useCongregationFilters(ref(all))
    filters.hideBranches.value = true
    expect(filters.filtered.value).toHaveLength(3)
    expect(filters.filtered.value.every((c) => c.type !== 'branch')).toBe(true)
  })

  it('searches without diacritics across name, city and parent', () => {
    const filters = useCongregationFilters(ref(all))
    filters.search.value = 'wroclaw'
    expect(filters.filtered.value.map((c) => c.name)).toEqual([
      'ZBÓR WE WROCŁAWIU',
      'Placówka Psie Pole',
    ])
  })

  it('combines filters', () => {
    const filters = useCongregationFilters(ref(all))
    filters.country.value = 'PL'
    filters.province.value = 'dolnoslaskie'
    filters.hideBranches.value = true
    expect(filters.filtered.value.map((c) => c.name)).toEqual(['ZBÓR WE WROCŁAWIU'])
  })

  it('clears a province that the newly selected country does not have', async () => {
    const filters = useCongregationFilters(ref(all))
    filters.province.value = 'dolnoslaskie'
    filters.country.value = 'DE'
    await nextTick()

    expect(filters.province.value).toBe(ANY_VALUE)
    expect(filters.filtered.value.map((c) => c.name)).toEqual(['ZBÓR W MARKTREDWITZ'])
  })

  it('reset restores every filter', () => {
    const filters = useCongregationFilters(ref(all))
    filters.search.value = 'x'
    filters.country.value = 'DE'
    filters.hideBranches.value = true

    filters.reset()

    expect(filters.isFiltered.value).toBe(false)
    expect(filters.filtered.value).toHaveLength(4)
  })

  it('reports whether any branch exists, to hide a useless toggle', () => {
    expect(useCongregationFilters(ref(all)).hasBranches.value).toBe(true)
    expect(useCongregationFilters(ref([wroclaw])).hasBranches.value).toBe(false)
  })
})
