import { describe, expect, it } from 'vitest'
import { matchesSearch, normalizeForSearch, searchTerms } from './search'

describe('normalizeForSearch', () => {
  it('lowercases and strips Polish diacritics', () => {
    expect(normalizeForSearch('Wrocław')).toBe('wroclaw')
    expect(normalizeForSearch('ŚWIEBODZIN')).toBe('swiebodzin')
    expect(normalizeForSearch('Kędzierzyn-Koźle')).toBe('kedzierzyn-kozle')
    expect(normalizeForSearch('Żory')).toBe('zory')
    expect(normalizeForSearch('Łódź')).toBe('lodz')
  })

  it('leaves ASCII untouched', () => {
    expect(normalizeForSearch('Marktredwitz')).toBe('marktredwitz')
  })
})

describe('searchTerms', () => {
  it('splits on whitespace and drops empties', () => {
    expect(searchTerms('  Zbór   Warszawa ')).toEqual(['zbor', 'warszawa'])
  })

  it('returns no terms for a blank query', () => {
    expect(searchTerms('   ')).toEqual([])
  })
})

describe('matchesSearch', () => {
  const fields = ['ZBÓR WE WROCŁAWIU', 'ul. Kwiatowa 1', null, 'dolnoslaskie']

  it('matches regardless of diacritics in the query or the data', () => {
    expect(matchesSearch(fields, searchTerms('wroclaw'))).toBe(true)
    expect(matchesSearch(fields, searchTerms('WROCŁAW'))).toBe(true)
  })

  it('requires every term to match, in any order', () => {
    expect(matchesSearch(fields, searchTerms('zbor kwiatowa'))).toBe(true)
    expect(matchesSearch(fields, searchTerms('kwiatowa zbor'))).toBe(true)
    expect(matchesSearch(fields, searchTerms('zbor gdansk'))).toBe(false)
  })

  it('matches everything when there are no terms', () => {
    expect(matchesSearch(fields, [])).toBe(true)
  })

  it('ignores null and undefined fields', () => {
    expect(matchesSearch([null, undefined, 'Gdańsk'], searchTerms('gdansk'))).toBe(true)
  })
})
