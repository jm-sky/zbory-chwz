import { describe, expect, it } from 'vitest'
import { formatDistance, haversineKm } from './distance'

const WARSAW = { lat: 52.2297, lng: 21.0122 }
const KRAKOW = { lat: 50.0647, lng: 19.9450 }

describe('haversineKm', () => {
  it('returns 0 for identical coordinates', () => {
    expect(haversineKm(WARSAW, WARSAW)).toBe(0)
  })

  it('matches the known straight-line distance between Warsaw and Kraków', () => {
    expect(haversineKm(WARSAW, KRAKOW)).toBeCloseTo(252, -1)
  })

  it('is symmetric', () => {
    expect(haversineKm(WARSAW, KRAKOW)).toBeCloseTo(haversineKm(KRAKOW, WARSAW), 6)
  })
})

describe('formatDistance', () => {
  it('formats sub-kilometer distances in meters', () => {
    expect(formatDistance(0.85)).toBe('850 m')
  })

  it('formats kilometer-scale distances with one decimal', () => {
    expect(formatDistance(3.2)).toBe('3.2 km')
    expect(formatDistance(252)).toBe('252.0 km')
  })
})
