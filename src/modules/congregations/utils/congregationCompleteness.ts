/**
 * Profile completeness scoring for congregations.
 *
 * IBAN and branches are intentionally excluded: IBAN is financial data not
 * shown as a "missing" public field, and branches don't apply to every
 * congregation. `name`/`city` are excluded because they're required at
 * creation time and therefore always present.
 */

export type CompletenessFieldKey =
  | 'description'
  | 'street'
  | 'postal_code'
  | 'province'
  | 'website'
  | 'email'
  | 'geolocation'
  | 'service_times'
  | 'card_contacts'

export const COMPLETENESS_WEIGHTS: Record<CompletenessFieldKey, number> = {
  description: 6,
  street: 16,
  postal_code: 16,
  province: 11,
  website: 6,
  email: 6,
  geolocation: 16,
  service_times: 13,
  card_contacts: 10,
}

export interface ICompletenessInput {
  description?: string | null
  street?: string | null
  postal_code?: string | null
  province?: string | null
  website?: string | null
  email?: string | null
  latitude?: number | null
  longitude?: number | null
  service_times_count?: number
  card_contacts_count?: number
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
    email: hasValue(input.email),
    geolocation: input.latitude != null && input.longitude != null,
    service_times: (input.service_times_count ?? 0) > 0,
    card_contacts: (input.card_contacts_count ?? 0) > 0,
  }

  const missingFields = (Object.keys(presence) as CompletenessFieldKey[]).filter((key) => !presence[key])
  const score = (Object.keys(presence) as CompletenessFieldKey[]).reduce(
    (total, key) => total + (presence[key] ? COMPLETENESS_WEIGHTS[key] : 0),
    0,
  )

  return { score, missingFields }
}
