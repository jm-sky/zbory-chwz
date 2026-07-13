import { computed, type ComputedRef, ref, type Ref, watch } from 'vue'
import type { ICongregationDetailed } from '../types/congregation.types'
import { contactsOf } from '../utils/exportCongregations'
import { matchesSearch, searchTerms } from '../utils/search'

/** Sentinel for "no filter", since Select cannot bind an empty string value. */
export const ANY_VALUE = 'any'

export interface ICongregationFilters {
  search: Ref<string>
  country: Ref<string>
  province: Ref<string>
  hideBranches: Ref<boolean>
  /** Countries present in the data, as ISO codes. */
  availableCountries: ComputedRef<string[]>
  /** Provinces present in the data, narrowed by the selected country. */
  availableProvinces: ComputedRef<string[]>
  hasBranches: ComputedRef<boolean>
  isFiltered: ComputedRef<boolean>
  filtered: ComputedRef<ICongregationDetailed[]>
  reset: () => void
}

function searchableFields(congregation: ICongregationDetailed): Array<string | null | undefined> {
  const contacts = contactsOf(congregation).flatMap((contact) => [
    contact.name,
    contact.title,
    contact.phone,
    contact.email,
  ])
  const serviceTimes = (congregation.service_times ?? []).flatMap((time) => [time.day, time.time, time.description])

  return [
    congregation.name,
    congregation.description,
    congregation.city,
    congregation.street,
    congregation.postal_code,
    congregation.province,
    congregation.parent_name,
    ...serviceTimes,
    ...contacts,
  ]
}

export function useCongregationFilters(
  congregations: Ref<ICongregationDetailed[] | undefined>,
): ICongregationFilters {
  const search = ref<string>('')
  const country = ref<string>(ANY_VALUE)
  const province = ref<string>(ANY_VALUE)
  const hideBranches = ref<boolean>(false)

  const items = computed<ICongregationDetailed[]>(() => congregations.value ?? [])

  const availableCountries = computed<string[]>(() =>
    [...new Set(items.value.map((item) => item.country).filter((code): code is string => !!code))].sort(),
  )

  // Selecting a country that has no rows for the chosen province would leave an
  // impossible combination, so provinces are scoped to the selected country.
  const availableProvinces = computed<string[]>(() => {
    const scoped = country.value === ANY_VALUE
      ? items.value
      : items.value.filter((item) => item.country === country.value)

    return [...new Set(scoped.map((item) => item.province).filter((p): p is string => !!p))].sort()
  })

  // Changing country can strand a province that no longer exists in the list,
  // which would silently filter everything out.
  watch(availableProvinces, (provinces) => {
    if (province.value === ANY_VALUE) return
    if (provinces.includes(province.value)) return
    // Keep URL-provided province while congregation data is still loading.
    if (provinces.length === 0 && items.value.length === 0) return
    province.value = ANY_VALUE
  })

  const hasBranches = computed<boolean>(() => items.value.some((item) => item.type === 'branch'))

  const isFiltered = computed<boolean>(
    () =>
      search.value.trim() !== ''
      || country.value !== ANY_VALUE
      || province.value !== ANY_VALUE
      || hideBranches.value,
  )

  const filtered = computed<ICongregationDetailed[]>(() => {
    const terms = searchTerms(search.value)

    return items.value.filter((congregation) => {
      if (hideBranches.value && congregation.type === 'branch') return false
      if (country.value !== ANY_VALUE && congregation.country !== country.value) return false
      if (province.value !== ANY_VALUE && congregation.province !== province.value) return false
      return matchesSearch(searchableFields(congregation), terms)
    })
  })

  function reset(): void {
    search.value = ''
    country.value = ANY_VALUE
    province.value = ANY_VALUE
    hideBranches.value = false
  }

  return {
    search,
    country,
    province,
    hideBranches,
    availableCountries,
    availableProvinces,
    hasBranches,
    isFiltered,
    filtered,
    reset,
  }
}
