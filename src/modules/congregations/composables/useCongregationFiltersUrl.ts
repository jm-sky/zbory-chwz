import { refDebounced } from '@vueuse/core'
import { nextTick, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ICongregationFilterQueryState } from '../utils/congregationFilterQuery'
import {
  areCongregationFilterQueriesEqual,
  buildCongregationFilterQuery,
  parseCongregationFilterQuery,
} from '../utils/congregationFilterQuery'
import { ANY_VALUE, type ICongregationFilters } from './useCongregationFilters'

export function useCongregationFiltersUrl(filters: ICongregationFilters): void {
  const route = useRoute()
  const router = useRouter()
  const debouncedSearch = refDebounced(filters.search, 300)

  let isUpdatingFromUrl = false

  function applyParsedState(parsed: ICongregationFilterQueryState): void {
    if (filters.search.value !== parsed.search) {
      filters.search.value = parsed.search
    }
    if (filters.country.value !== parsed.country) {
      filters.country.value = parsed.country
    }
    if (filters.province.value !== parsed.province) {
      filters.province.value = parsed.province
    }
    if (filters.hideBranches.value !== parsed.hideBranches) {
      filters.hideBranches.value = parsed.hideBranches
    }
    if (filters.maxDistanceKm.value !== parsed.maxDistanceKm) {
      filters.maxDistanceKm.value = parsed.maxDistanceKm
    }
    if (filters.sortByDistance.value !== parsed.sortByDistance) {
      filters.sortByDistance.value = parsed.sortByDistance
    }
  }

  function syncFromUrl(): void {
    if (isUpdatingFromUrl) return

    isUpdatingFromUrl = true
    applyParsedState(parseCongregationFilterQuery(route.query))
    nextTick(() => {
      isUpdatingFromUrl = false
    })
  }

  function syncToUrl(): void {
    if (isUpdatingFromUrl) return

    const nextQuery = buildCongregationFilterQuery({
      search: debouncedSearch.value,
      country: filters.country.value,
      province: filters.province.value,
      hideBranches: filters.hideBranches.value,
      maxDistanceKm: filters.maxDistanceKm.value,
      sortByDistance: filters.sortByDistance.value,
    })

    if (areCongregationFilterQueriesEqual(route.query, nextQuery)) return

    router.replace({ query: nextQuery }).catch(() => {
      // Ignore redundant navigation errors
    })
  }

  syncFromUrl()

  const urlWatchStop = watch(() => route.query, () => {
    syncFromUrl()
  })

  const stateWatchStop = watch(
    [
      debouncedSearch,
      () => filters.country.value,
      () => filters.province.value,
      () => filters.hideBranches.value,
      () => filters.maxDistanceKm.value,
      () => filters.sortByDistance.value,
    ],
    () => {
      syncToUrl()
    },
  )

  const countryValidationStop = watch(filters.availableCountries, (countries) => {
    if (isUpdatingFromUrl) return
    if (countries.length === 0) return
    if (filters.country.value !== ANY_VALUE && !countries.includes(filters.country.value)) {
      filters.country.value = ANY_VALUE
    }
  })

  onBeforeUnmount(() => {
    urlWatchStop()
    stateWatchStop()
    countryValidationStop()
  })
}
