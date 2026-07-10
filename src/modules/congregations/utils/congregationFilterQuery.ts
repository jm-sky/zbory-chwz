import { ANY_VALUE } from '../composables/useCongregationFilters'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

export const CONGREGATION_FILTER_QUERY_KEYS = ['q', 'country', 'province', 'hideBranches'] as const

export interface ICongregationFilterQueryState {
  search: string
  country: string
  province: string
  hideBranches: boolean
}

function queryString(value: LocationQuery[string] | LocationQueryRaw[string]): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function parseHideBranches(value: LocationQuery[string] | LocationQueryRaw[string]): boolean {
  const raw = queryString(value)
  return raw === '1' || raw === 'true'
}

export function parseCongregationFilterQuery(query: LocationQuery | LocationQueryRaw): ICongregationFilterQueryState {
  const search = queryString(query.q) ?? ''
  const countryRaw = queryString(query.country)
  const provinceRaw = queryString(query.province)

  return {
    search,
    country: countryRaw && countryRaw.length > 0 ? countryRaw : ANY_VALUE,
    province: provinceRaw && provinceRaw.length > 0 ? provinceRaw : ANY_VALUE,
    hideBranches: parseHideBranches(query.hideBranches),
  }
}

export function buildCongregationFilterQuery(state: ICongregationFilterQueryState): LocationQueryRaw {
  const query: LocationQueryRaw = {}

  if (state.search.trim()) {
    query.q = state.search
  }

  if (state.country !== ANY_VALUE) {
    query.country = state.country
  }

  if (state.province !== ANY_VALUE) {
    query.province = state.province
  }

  if (state.hideBranches) {
    query.hideBranches = '1'
  }

  return query
}

function normalizedFilterQuery(query: LocationQuery | LocationQueryRaw): Record<string, string> {
  const parsed = parseCongregationFilterQuery(query)
  const built = buildCongregationFilterQuery(parsed)
  const normalized: Record<string, string> = {}

  for (const key of CONGREGATION_FILTER_QUERY_KEYS) {
    const value = built[key]
    if (typeof value === 'string') {
      normalized[key] = value
    }
  }

  return normalized
}

export function areCongregationFilterQueriesEqual(
  a: LocationQuery | LocationQueryRaw,
  b: LocationQuery | LocationQueryRaw,
): boolean {
  const left = normalizedFilterQuery(a)
  const right = normalizedFilterQuery(b)
  const keys = new Set([...Object.keys(left), ...Object.keys(right)])

  for (const key of keys) {
    if (left[key] !== right[key]) {
      return false
    }
  }

  return true
}
