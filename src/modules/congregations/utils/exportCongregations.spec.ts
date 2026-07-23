import { describe, expect, it } from 'vitest'
import type { ICongregationDetailed } from '../types/congregation.types'
import {
  contactsOf,
  exportFilename,
  type IExportLabels,
  toJson,
  toMarkdown,
} from './exportCongregations'

const labels: IExportLabels = {
  title: 'Zbory CHWZ',
  exportedAt: 'Wyeksportowano',
  count: 'Liczba pozycji',
  branchOf: 'Placówka zboru',
  address: 'Adres',
  serviceTimes: 'Nabożeństwa',
  contact: 'Kontakt',
}

const now = new Date('2026-07-10T08:30:00Z')
const options = { locale: 'pl', labels, now }

const church: ICongregationDetailed = {
  id: 'c1',
  name: 'ZBÓR WE WROCŁAWIU',
  description: 'Opis zboru',
  status: 'published',
  createdAt: '2026-01-01T00:00:00Z',
  type: 'church',
  city: 'Wrocław',
  street: 'ul. Kwiatowa 1',
  postal_code: '50-001',
  province: 'dolnoslaskie',
  country: 'PL',
  service_times: [{ day: 'niedziela', time: '10:00' }],
  card_contacts: [{ name: 'Jan Kowalski', title: 'Pastor', phone: '123', email: 'a@b.pl' }],
}

const branch: ICongregationDetailed = {
  id: 'b1',
  name: 'Placówka Psie Pole',
  createdAt: '2026-02-01T00:00:00Z',
  type: 'branch',
  parent_id: 'c1',
  parent_name: 'ZBÓR WE WROCŁAWIU',
  city: 'Wrocław',
  province: 'dolnoslaskie',
  country: 'PL',
}

describe('contactsOf', () => {
  it('prefers card_contacts and drops unnamed entries', () => {
    const congregation = {
      ...church,
      card_contacts: [{ name: 'Ala' }, { name: null, phone: '999' }],
    }
    expect(contactsOf(congregation)).toEqual([{ name: 'Ala' }])
  })

  it('falls back to the legacy single contact', () => {
    const congregation: ICongregationDetailed = {
      ...church,
      card_contacts: [],
      contact_name: 'Ewa',
      contact_title: 'Diakon',
      contact_phone: '111',
      contact_email: 'e@f.pl',
    }
    expect(contactsOf(congregation)).toEqual([
      { name: 'Ewa', title: 'Diakon', phone: '111', email: 'e@f.pl' },
    ])
  })

  it('returns nothing when there is no contact at all', () => {
    expect(contactsOf(branch)).toEqual([])
  })
})

describe('exportFilename', () => {
  it('embeds the date and the format extension', () => {
    expect(exportFilename('json', now)).toBe('zbory-chwz-2026-07-10.json')
    expect(exportFilename('markdown', now)).toBe('zbory-chwz-2026-07-10.md')
  })
})

describe('toJson', () => {
  it('exports codes alongside their localized labels', () => {
    const payload = JSON.parse(toJson([church], options))

    expect(payload.count).toBe(1)
    expect(payload.exportedAt).toBe('2026-07-10T08:30:00.000Z')
    expect(payload.congregations[0].address).toMatchObject({
      country: 'PL',
      countryLabel: 'Polska',
      province: 'dolnoslaskie',
      provinceLabel: 'dolnośląskie',
      city: 'Wrocław',
    })
  })

  it('marks a branch and names its parent', () => {
    const payload = JSON.parse(toJson([branch], options))
    expect(payload.congregations[0]).toMatchObject({
      type: 'branch',
      parentName: 'ZBÓR WE WROCŁAWIU',
    })
  })

  it('only exports what it is given, so filters carry through', () => {
    expect(JSON.parse(toJson([], options)).congregations).toEqual([])
  })
})

describe('toMarkdown', () => {
  it('renders a heading, address, services and contacts', () => {
    const markdown = toMarkdown([church], options)

    expect(markdown).toContain('# Zbory CHWZ')
    expect(markdown).toContain('Liczba pozycji: 1')
    expect(markdown).toContain('## ZBÓR WE WROCŁAWIU')
    expect(markdown).toContain('- **Adres:** ul. Kwiatowa 1, 50-001 Wrocław, dolnośląskie, Polska')
    expect(markdown).toContain('- **Nabożeństwa:** niedziela 10:00')
    expect(markdown).toContain('- **Kontakt:** Jan Kowalski (Pastor) — 123, a@b.pl')
  })

  it('labels a branch with its parent congregation', () => {
    const markdown = toMarkdown([branch], options)
    expect(markdown).toContain('*Placówka zboru: ZBÓR WE WROCŁAWIU*')
  })

  it('omits sections that have no data', () => {
    const markdown = toMarkdown([branch], options)
    expect(markdown).not.toContain('**Nabożeństwa:**')
    expect(markdown).not.toContain('**Kontakt:**')
  })
})
