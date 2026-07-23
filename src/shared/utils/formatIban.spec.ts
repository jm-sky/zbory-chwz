import { describe, expect, it } from 'vitest'
import { formatIban } from './formatIban'

describe('formatIban', () => {
  it('should format a Polish IBAN in domestic NRB style, dropping the PL prefix', () => {
    expect(formatIban('PL61109010140000071219812874')).toBe('61 1090 1014 0000 0712 1981 2874')
  })

  it('should reformat a Polish IBAN with inconsistent spacing', () => {
    expect(formatIban('pl 6110 9010 1400 0007 1219 8128 74')).toBe('61 1090 1014 0000 0712 1981 2874')
  })

  it('should format a foreign IBAN in standard groups of 4, keeping the country prefix', () => {
    expect(formatIban('DE89370400440532013000')).toBe('DE89 3704 0044 0532 0130 00')
  })

  it('should return an empty string for null or undefined', () => {
    expect(formatIban(null)).toBe('')
    expect(formatIban(undefined)).toBe('')
  })

  it('should return an empty string for an empty string', () => {
    expect(formatIban('')).toBe('')
  })
})
