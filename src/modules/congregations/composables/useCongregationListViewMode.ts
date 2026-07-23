import { useLocalStorage } from '@vueuse/core'
import type { CongregationListViewMode } from '../types/congregationListView.types'

const STORAGE_KEY = 'congregations-list-view-mode'
const DEFAULT_MODE: CongregationListViewMode = 'grid'
const VALID_MODES: CongregationListViewMode[] = ['list', 'grid', 'map']

function isValidMode(value: string): value is CongregationListViewMode {
  return VALID_MODES.includes(value as CongregationListViewMode)
}

export function useCongregationListViewMode() {
  const viewMode = useLocalStorage<CongregationListViewMode>(STORAGE_KEY, DEFAULT_MODE, {
    flush: 'sync',
    serializer: {
      read: (raw) => (isValidMode(raw) ? raw : DEFAULT_MODE),
      write: (value) => value,
    },
  })

  return { viewMode }
}
