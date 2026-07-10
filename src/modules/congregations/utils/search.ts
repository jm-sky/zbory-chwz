/**
 * Diacritics-insensitive search over the congregation list.
 *
 * The list is small enough (tens of congregations) to filter in the browser, so
 * this stands in for the Postgres full-text search tracked in issue #011.
 */

/** `ł` has no combining-mark decomposition, so NFD alone will not strip it. */
const NON_DECOMPOSING = /ł/g

const COMBINING_MARKS = /[\u0300-\u036f]/g

/** Lowercase, strip diacritics: 'Wrocław' -> 'wroclaw'. */
export function normalizeForSearch(value: string): string {
  return value
    .toLowerCase()
    .replace(NON_DECOMPOSING, 'l')
    .normalize('NFD')
    .replace(COMBINING_MARKS, '')
}

/** Split a query into terms; every term must match (AND), in any order. */
export function searchTerms(query: string): string[] {
  return normalizeForSearch(query).split(/\s+/).filter(Boolean)
}

/** True when every term appears somewhere in the haystack fields. */
export function matchesSearch(fields: Array<string | null | undefined>, terms: string[]): boolean {
  if (terms.length === 0) return true
  const haystack = normalizeForSearch(fields.filter(Boolean).join(' '))
  return terms.every((term) => haystack.includes(term))
}
