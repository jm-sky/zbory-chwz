import { describe, expect, it } from 'vitest'
import { calculateCongregationCompleteness, COMPLETENESS_WEIGHTS } from './congregationCompleteness'

describe('COMPLETENESS_WEIGHTS', () => {
  it('sums to 100', () => {
    const total = Object.values(COMPLETENESS_WEIGHTS).reduce((sum, weight) => sum + weight, 0)
    expect(total).toBe(100)
  })
})

describe('calculateCongregationCompleteness', () => {
  it('scores 0 and lists every field as missing for an empty profile', () => {
    const result = calculateCongregationCompleteness({})
    expect(result.score).toBe(0)
    expect(result.missingFields).toEqual(Object.keys(COMPLETENESS_WEIGHTS))
  })

  it('scores 100 with no missing fields when every field is present', () => {
    const result = calculateCongregationCompleteness({
      description: 'Opis zboru',
      street: 'ul. Kwiatowa 1',
      postal_code: '00-001',
      province: 'mazowieckie',
      website: 'https://example.com',
      latitude: 52.23,
      longitude: 21.01,
      service_times_count: 2,
      card_contacts_count: 1,
      has_contact_email: true,
      has_contact_phone: true,
    })
    expect(result.score).toBe(100)
    expect(result.missingFields).toEqual([])
  })

  it('scores card_contacts, contact_email and contact_phone independently', () => {
    const result = calculateCongregationCompleteness({
      card_contacts_count: 1,
      has_contact_email: false,
      has_contact_phone: true,
    })
    expect(result.missingFields).not.toContain('card_contacts')
    expect(result.missingFields).toContain('contact_email')
    expect(result.missingFields).not.toContain('contact_phone')
    expect(result.score).toBe(COMPLETENESS_WEIGHTS.card_contacts + COMPLETENESS_WEIGHTS.contact_phone)
  })

  it('sums only the weights of present fields', () => {
    const result = calculateCongregationCompleteness({
      street: 'ul. Kwiatowa 1',
      postal_code: '00-001',
    })
    expect(result.score).toBe(COMPLETENESS_WEIGHTS.street + COMPLETENESS_WEIGHTS.postal_code)
    expect(result.missingFields).not.toContain('street')
    expect(result.missingFields).not.toContain('postal_code')
  })

  it('treats blank/whitespace strings as missing', () => {
    const result = calculateCongregationCompleteness({ description: '   ' })
    expect(result.missingFields).toContain('description')
  })

  it('requires both latitude and longitude for geolocation credit', () => {
    expect(calculateCongregationCompleteness({ latitude: 52.23 }).missingFields).toContain('geolocation')
    expect(calculateCongregationCompleteness({ longitude: 21.01 }).missingFields).toContain('geolocation')
    expect(calculateCongregationCompleteness({ latitude: 52.23, longitude: 21.01 }).missingFields).not.toContain('geolocation')
  })

  it('treats a zero count as missing for list-backed fields', () => {
    const result = calculateCongregationCompleteness({ service_times_count: 0, card_contacts_count: 0 })
    expect(result.missingFields).toContain('service_times')
    expect(result.missingFields).toContain('card_contacts')
  })
})
