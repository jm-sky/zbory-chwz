/**
 * Countries are stored as ISO 3166-1 alpha-2 codes and rendered with
 * `Intl.DisplayNames`, so a new country needs no translation entries.
 */

/** Countries offered when editing an address. Extend as congregations appear. */
export const COUNTRY_CODES: readonly string[] = [
  'PL',
  'DE',
  'AT',
  'BE',
  'BY',
  'CZ',
  'DK',
  'ES',
  'FR',
  'GB',
  'IE',
  'IS',
  'IT',
  'LT',
  'LV',
  'NL',
  'NO',
  'SE',
  'SK',
  'UA',
  'US',
  'CA',
]

export const DEFAULT_COUNTRY_CODE = 'PL'

/** ISO 3166-2:PL — voivodeship slugs, matching `backend/app/modules/congregations/geo.py`. */
export const POLISH_PROVINCES: readonly string[] = [
  'dolnoslaskie',
  'kujawsko-pomorskie',
  'lubelskie',
  'lubuskie',
  'lodzkie',
  'malopolskie',
  'mazowieckie',
  'opolskie',
  'podkarpackie',
  'podlaskie',
  'pomorskie',
  'slaskie',
  'swietokrzyskie',
  'warminsko-mazurskie',
  'wielkopolskie',
  'zachodniopomorskie',
]

const PROVINCES_BY_COUNTRY: Record<string, readonly string[]> = {
  PL: POLISH_PROVINCES,
}

/** Voivodeship slugs carry no diacritics; restore them for display. */
const POLISH_PROVINCE_LABELS: Record<string, string> = {
  'dolnoslaskie': 'dolnośląskie',
  'kujawsko-pomorskie': 'kujawsko-pomorskie',
  'lubelskie': 'lubelskie',
  'lubuskie': 'lubuskie',
  'lodzkie': 'łódzkie',
  'malopolskie': 'małopolskie',
  'mazowieckie': 'mazowieckie',
  'opolskie': 'opolskie',
  'podkarpackie': 'podkarpackie',
  'podlaskie': 'podlaskie',
  'pomorskie': 'pomorskie',
  'slaskie': 'śląskie',
  'swietokrzyskie': 'świętokrzyskie',
  'warminsko-mazurskie': 'warmińsko-mazurskie',
  'wielkopolskie': 'wielkopolskie',
  'zachodniopomorskie': 'zachodniopomorskie',
}

export function provincesForCountry(countryCode: string): readonly string[] {
  return PROVINCES_BY_COUNTRY[countryCode] ?? []
}

export function provinceLabel(province: string): string {
  return POLISH_PROVINCE_LABELS[province] ?? province
}

/**
 * Localized country name, e.g. 'PL' -> 'Polska' (pl) / 'Poland' (en).
 * Falls back to the raw code where `Intl.DisplayNames` is unavailable.
 */
export function countryLabel(countryCode: string, locale: string): string {
  try {
    const displayNames = new Intl.DisplayNames([locale], { type: 'region' })
    return displayNames.of(countryCode) ?? countryCode
  } catch {
    return countryCode
  }
}

export interface ICountryOption {
  code: string
  label: string
}

/** Country options sorted by localized name, with the default country first. */
export function countryOptions(locale: string): ICountryOption[] {
  const collator = new Intl.Collator(locale)
  return COUNTRY_CODES.map<ICountryOption>((code) => ({ code, label: countryLabel(code, locale) }))
    .sort((a, b) => {
      if (a.code === DEFAULT_COUNTRY_CODE) return -1
      if (b.code === DEFAULT_COUNTRY_CODE) return 1
      return collator.compare(a.label, b.label)
    })
}
