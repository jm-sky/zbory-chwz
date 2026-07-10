import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { getPolishPluralizationRule } from '@/shared/i18n/config/getPolishPluralizationRule'
import { congregationsEn } from './locales/en'
import { congregationsPl } from './locales/pl'

function collectKeys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix]
  return Object.entries(value).flatMap(([key, child]) =>
    collectKeys(child, prefix ? `${prefix}.${key}` : key),
  )
}

const i18n = createI18n({
  legacy: false,
  locale: 'pl',
  messages: { en: congregationsEn, pl: congregationsPl },
  pluralRules: { pl: getPolishPluralizationRule },
})

const t = i18n.global.t

describe('congregation translations', () => {
  it('define the same keys in Polish and English', () => {
    expect(collectKeys(congregationsPl).sort()).toEqual(collectKeys(congregationsEn).sort())
  })

  it('cover every key the filter bar and export menu use', () => {
    const used = [
      'congregations.filters.searchPlaceholder',
      'congregations.filters.country',
      'congregations.filters.anyCountry',
      'congregations.filters.province',
      'congregations.filters.anyProvince',
      'congregations.filters.hideBranches',
      'congregations.filters.reset',
      'congregations.filters.resultCount',
      'congregations.export.button',
      'congregations.export.json',
      'congregations.export.markdown',
      'congregations.list.branch',
      'congregations.list.branchOf',
    ]
    const known = collectKeys(congregationsPl)
    for (const key of used) expect(known).toContain(key)
  })

  it('interpolates the parent congregation name', () => {
    expect(t('congregations.list.branchOf', { name: 'ZBÓR WE WROCŁAWIU' })).toBe(
      'Placówka zboru ZBÓR WE WROCŁAWIU',
    )
  })

  it('picks the right Polish plural form for the result count', () => {
    const count = (n: number) => t('congregations.filters.resultCount', { count: n }, n)

    expect(count(0)).toBe('Brak zborów')
    expect(count(1)).toBe('1 zbór')
    expect(count(3)).toBe('3 zbory')
    expect(count(5)).toBe('5 zborów')
    // 12-14 are "many", unlike 22-24 which are "few"
    expect(count(12)).toBe('12 zborów')
    expect(count(22)).toBe('22 zbory')
  })

  it('picks the right English plural form', () => {
    i18n.global.locale.value = 'en'
    const count = (n: number) => t('congregations.filters.resultCount', { count: n }, n)

    expect(count(0)).toBe('No congregations')
    expect(count(1)).toBe('1 congregation')
    expect(count(7)).toBe('7 congregations')
    i18n.global.locale.value = 'pl'
  })
})
