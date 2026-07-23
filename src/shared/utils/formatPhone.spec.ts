import { describe, expect, it } from 'vitest'
import { formatPhoneNumber } from './formatPhone'

describe('formatPhoneNumber', () => {
  it('should format a 9-digit local number with +48 prefix', () => {
    expect(formatPhoneNumber('501234567')).toBe('+48 501 234 567')
  })

  it('should format a number already containing the 48 prefix', () => {
    expect(formatPhoneNumber('+48501234567')).toBe('+48 501 234 567')
  })

  it('should reformat a number with inconsistent spacing', () => {
    expect(formatPhoneNumber('48 501 234 567')).toBe('+48 501 234 567')
  })

  it('should return an empty string for null or undefined', () => {
    expect(formatPhoneNumber(null)).toBe('')
    expect(formatPhoneNumber(undefined)).toBe('')
  })

  it('should return an empty string for an empty string', () => {
    expect(formatPhoneNumber('')).toBe('')
  })

  it('should return the original value unchanged for non-Polish-shaped numbers', () => {
    expect(formatPhoneNumber('+1 555 123 4567')).toBe('+1 555 123 4567')
  })
})
