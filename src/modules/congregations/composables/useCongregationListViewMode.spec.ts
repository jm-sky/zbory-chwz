import { beforeEach, describe, expect, it } from 'vitest'
import { useCongregationListViewMode } from './useCongregationListViewMode'

describe('useCongregationListViewMode', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('should default to grid when nothing is stored', () => {
    const { viewMode } = useCongregationListViewMode()
    expect(viewMode.value).toBe('grid')
  })

  it('should persist the selected mode to localStorage', () => {
    const { viewMode } = useCongregationListViewMode()
    viewMode.value = 'list'
    expect(localStorage.getItem('congregations-list-view-mode')).toBe('list')
  })

  it('should read a previously stored valid mode', () => {
    localStorage.setItem('congregations-list-view-mode', 'list')
    const { viewMode } = useCongregationListViewMode()
    expect(viewMode.value).toBe('list')
  })

  it('should fall back to grid for an invalid stored value', () => {
    localStorage.setItem('congregations-list-view-mode', 'invalid-mode')
    const { viewMode } = useCongregationListViewMode()
    expect(viewMode.value).toBe('grid')
  })

  it('should read a previously stored map mode', () => {
    localStorage.setItem('congregations-list-view-mode', 'map')
    const { viewMode } = useCongregationListViewMode()
    expect(viewMode.value).toBe('map')
  })
})
