<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ICongregationWithDistance } from '../../composables/useCongregationFilters'
import type { ILatLng } from '../../utils/distance'
import type { IMapMarker } from './LeafletMapBase.vue'
import { formatDistance } from '../../utils/distance'
import LeafletMapBase from './LeafletMapBase.vue'

const USER_MARKER_ID = '__user-location__'

const { t } = useI18n()

const { congregations, userLocation = null } = defineProps<{
  congregations: ICongregationWithDistance[]
  userLocation?: ILatLng | null
}>()

const emit = defineEmits<{ open: [id: string] }>()

function escapeHtml(value: string): string {
  const div = document.createElement('div')
  div.textContent = value
  return div.innerHTML
}

const withCoordinates = computed<ICongregationWithDistance[]>(
  () => congregations.filter(c => c.latitude != null && c.longitude != null),
)

const missingCount = computed<number>(() => congregations.length - withCoordinates.value.length)

const markers = computed<IMapMarker[]>(() => {
  const congregationMarkers: IMapMarker[] = withCoordinates.value.map(c => ({
    id: c.id,
    lat: c.latitude as number,
    lng: c.longitude as number,
    tooltipHtml: c.distanceKm != null
      ? `<div>${escapeHtml(c.name)}</div><div class="text-muted-foreground">${formatDistance(c.distanceKm)}</div>`
      : escapeHtml(c.name),
  }))

  if (!userLocation) return congregationMarkers

  return [
    ...congregationMarkers,
    { id: USER_MARKER_ID, lat: userLocation.lat, lng: userLocation.lng, variant: 'user', tooltipHtml: t('congregations.list.filters.myLocation') },
  ]
})

const center = computed<{ lat: number, lng: number }>(() => {
  if (userLocation) return userLocation
  const first = withCoordinates.value[0]
  if (first) return { lat: first.latitude as number, lng: first.longitude as number }
  return { lat: 52.0, lng: 19.0 }
})

function onMarkerClick(payload: { id: string }): void {
  if (payload.id === USER_MARKER_ID) return
  emit('open', payload.id)
}
</script>

<template>
  <div class="space-y-2">
    <div class="h-[32rem] overflow-hidden rounded-lg border">
      <LeafletMapBase
        :center
        :zoom="6"
        :markers
        fit-to-markers
        @marker-click="onMarkerClick"
      />
    </div>
    <p v-if="missingCount > 0" class="text-xs text-muted-foreground">
      {{ t('congregations.list.view.mapMissingCoordinates', { count: missingCount }, missingCount) }}
    </p>
  </div>
</template>
