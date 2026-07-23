import { describe, expect, it } from 'vitest'
import { ANY_VALUE } from '../composables/useCongregationFilters'
import {
  areCongregationFilterQueriesEqual,
  buildCongregationFilterQuery,
  parseCongregationFilterQuery,
} from './congregationFilterQuery'

describe('congregationFilterQuery', () => {
  it('parses empty query to defaults', () => {
    expect(parseCongregationFilterQuery({})).toEqual({
      search: '',
      country: ANY_VALUE,
      province: ANY_VALUE,
      hideBranches: false,
      maxDistanceKm: null,
      sortByDistance: false,
    })
  })

  it('parses full query', () => {
    expect(parseCongregationFilterQuery({
      q: 'wroclaw',
      country: 'PL',
      province: 'dolnoslaskie',
      hideBranches: '1',
      maxDistanceKm: '25',
      sortByDistance: '1',
    })).toEqual({
      search: 'wroclaw',
      country: 'PL',
      province: 'dolnoslaskie',
      hideBranches: true,
      maxDistanceKm: 25,
      sortByDistance: true,
    })
  })

  it('parses hideBranches=true', () => {
    expect(parseCongregationFilterQuery({ hideBranches: 'true' }).hideBranches).toBe(true)
  })

  it('ignores a non-numeric or non-positive maxDistanceKm', () => {
    expect(parseCongregationFilterQuery({ maxDistanceKm: 'abc' }).maxDistanceKm).toBeNull()
    expect(parseCongregationFilterQuery({ maxDistanceKm: '-5' }).maxDistanceKm).toBeNull()
    expect(parseCongregationFilterQuery({ maxDistanceKm: '0' }).maxDistanceKm).toBeNull()
  })

  it('build omits default values', () => {
    expect(buildCongregationFilterQuery({
      search: '',
      country: ANY_VALUE,
      province: ANY_VALUE,
      hideBranches: false,
      maxDistanceKm: null,
      sortByDistance: false,
    })).toEqual({})
  })

  it('build includes non-default values', () => {
    expect(buildCongregationFilterQuery({
      search: 'warszawa',
      country: 'PL',
      province: 'mazowieckie',
      hideBranches: true,
      maxDistanceKm: 10,
      sortByDistance: true,
    })).toEqual({
      q: 'warszawa',
      country: 'PL',
      province: 'mazowieckie',
      hideBranches: '1',
      maxDistanceKm: '10',
      sortByDistance: '1',
    })
  })

  it('round-trips parse → build → parse', () => {
    const initial = {
      q: 'test',
      country: 'DE',
      province: 'bayern',
      hideBranches: '1',
      maxDistanceKm: '50',
      sortByDistance: '1',
    }
    const parsed = parseCongregationFilterQuery(initial)
    const built = buildCongregationFilterQuery(parsed)
    expect(parseCongregationFilterQuery(built)).toEqual(parsed)
  })

  it('treats equivalent queries as equal', () => {
    expect(areCongregationFilterQueriesEqual(
      { q: 'x', country: 'PL', hideBranches: '1' },
      { q: 'x', country: 'PL', hideBranches: 'true', extra: 'ignored' },
    )).toBe(true)
  })

  it('detects different queries', () => {
    expect(areCongregationFilterQueriesEqual(
      { q: 'a' },
      { q: 'b' },
    )).toBe(false)
  })

  it('treats empty and missing filter keys as equal', () => {
    expect(areCongregationFilterQueriesEqual({}, { country: '', province: '' })).toBe(true)
  })
})
