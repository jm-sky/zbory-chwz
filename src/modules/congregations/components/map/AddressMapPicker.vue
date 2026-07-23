<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { IMapMarker } from './LeafletMapBase.vue'
import LeafletMapBase from './LeafletMapBase.vue'

const MARKER_ID = 'address'
// Roughly the geographic center of Poland, used as a starting point until a
// pin has been placed.
const DEFAULT_CENTER = { lat: 52.0, lng: 19.0 }

const { t } = useI18n()

const latitude = defineModel<number | null>('latitude', { required: true })
const longitude = defineModel<number | null>('longitude', { required: true })

const hasCoordinates = computed<boolean>(() => latitude.value != null && longitude.value != null)

const center = computed<{ lat: number, lng: number }>(() => hasCoordinates.value
  ? { lat: latitude.value as number, lng: longitude.value as number }
  : DEFAULT_CENTER,
)

const markers = computed<IMapMarker[]>(() => hasCoordinates.value
  ? [{ id: MARKER_ID, lat: center.value.lat, lng: center.value.lng, draggable: true }]
  : [],
)

function setPosition(lat: number, lng: number): void {
  latitude.value = Math.round(lat * 1e7) / 1e7
  longitude.value = Math.round(lng * 1e7) / 1e7
}

function onMapClick(payload: { lat: number, lng: number }): void {
  setPosition(payload.lat, payload.lng)
}

function onMarkerDragend(payload: { id: string, lat: number, lng: number }): void {
  setPosition(payload.lat, payload.lng)
}
</script>

<template>
  <div class="space-y-2">
    <div class="h-56 overflow-hidden rounded-md border">
      <LeafletMapBase
        :center
        :zoom="hasCoordinates ? 15 : 6"
        :markers
        @map-click="onMapClick"
        @marker-dragend="onMarkerDragend"
      />
    </div>
    <p class="text-xs text-muted-foreground">
      {{ hasCoordinates ? t('congregations.edit.address.mapDragHint') : t('congregations.edit.address.mapClickHint') }}
    </p>
  </div>
</template>
