// shared/composables/useGeolocation.ts
import { useGeolocation as useVueUseGeolocation } from '@vueuse/core'
import { computed } from 'vue'

export interface ICoordinates {
  lat: number
  lng: number
}

/**
 * Thin wrapper over @vueuse/core's useGeolocation: doesn't request the
 * browser's permission prompt until locate() is called, so visiting a page
 * never triggers it unprompted - only an explicit "use my location" click does.
 */
export function useGeolocation() {
  const { coords, error, isSupported, resume } = useVueUseGeolocation({ immediate: false })

  const coordinates = computed<ICoordinates | null>(() => {
    if (!Number.isFinite(coords.value.latitude) || !Number.isFinite(coords.value.longitude)) return null
    return { lat: coords.value.latitude, lng: coords.value.longitude }
  })

  function locate(): void {
    resume()
  }

  return { coordinates, error, isSupported, locate }
}
