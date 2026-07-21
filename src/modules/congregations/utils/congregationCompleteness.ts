import type { ICongregationDetail } from '../types/congregation.types'

/**
 * Profile completeness scoring for congregations.
 *
 * IBAN and branches are intentionally excluded: IBAN is financial data not
 * shown as a "missing" public field, and branches don't apply to every
 * congregation. `name`/`city` are excluded because they're required at
 * creation time and therefore always present.
 *
 * The congregation's own top-level email is not scored either — it's
 * optional and many congregations only have contact persons, not an
 * institutional address. Instead, `card_contacts` is split into three
 * signals: having a contact person at all, one with an email, and one with
 * a phone (can be different people).
 */

export type CompletenessFieldKey =
  | 'description'
  | 'street'
  | 'postal_code'
  | 'province'
  | 'website'
  | 'geolocation'
  | 'service_times'
  | 'card_contacts'
  | 'contact_email'
  | 'contact_phone'

export const COMPLETENESS_WEIGHTS: Record<CompletenessFieldKey, number> = {
  description: 6,
  street: 16,
  postal_code: 16,
  province: 11,
  website: 6,
  geolocation: 16,
  service_times: 13,
  card_contacts: 6,
  contact_email: 5,
  contact_phone: 5,
}

export interface ICompletenessInput {
  description?: string | null
  street?: string | null
  postal_code?: string | null
  province?: string | null
  website?: string | null
  latitude?: number | null
  longitude?: number | null
  service_times_count?: number
  card_contacts_count?: number
  has_contact_email?: boolean
  has_contact_phone?: boolean
}

export interface ICompletenessResult {
  score: number
  missingFields: CompletenessFieldKey[]
}

function hasValue(value: string | null | undefined): boolean {
  return !!value?.trim()
}

export function calculateCongregationCompleteness(input: ICompletenessInput): ICompletenessResult {
  const presence: Record<CompletenessFieldKey, boolean> = {
    description: hasValue(input.description),
    street: hasValue(input.street),
    postal_code: hasValue(input.postal_code),
    province: hasValue(input.province),
    website: hasValue(input.website),
    geolocation: input.latitude != null && input.longitude != null,
    service_times: (input.service_times_count ?? 0) > 0,
    card_contacts: (input.card_contacts_count ?? 0) > 0,
    contact_email: !!input.has_contact_email,
    contact_phone: !!input.has_contact_phone,
  }

  const missingFields = (Object.keys(presence) as CompletenessFieldKey[]).filter((key) => !presence[key])
  const score = (Object.keys(presence) as CompletenessFieldKey[]).reduce(
    (total, key) => total + (presence[key] ? COMPLETENESS_WEIGHTS[key] : 0),
    0,
  )

  return { score, missingFields }
}

/** Maps a congregation detail response to completeness input, including hidden contacts. */
export function calculateCongregationCompletenessFromDetail(congregation: ICongregationDetail): ICompletenessResult {
  const allContacts = [
    ...congregation.card_contacts,
    ...(congregation.hidden_contacts ?? []),
  ]

  return calculateCongregationCompleteness({
    description: congregation.description,
    street: congregation.street,
    postal_code: congregation.postal_code,
    province: congregation.province,
    website: congregation.website,
    latitude: congregation.latitude,
    longitude: congregation.longitude,
    service_times_count: congregation.service_times.length,
    card_contacts_count: allContacts.length,
    has_contact_email: allContacts.some(contact => !!contact.email?.trim()),
    has_contact_phone: allContacts.some(contact => !!contact.phone?.trim()),
  })
}
