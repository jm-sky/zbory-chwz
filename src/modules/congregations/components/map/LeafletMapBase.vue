<script setup lang="ts">
import { onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { config } from '@/shared/config/config'
import type { Map as LeafletMap, Marker as LeafletMarker } from 'leaflet'

export interface IMapMarker {
  id: string
  lat: number
  lng: number
  /** Shown on click; use for a single-marker map where clicking has no other effect. */
  popupHtml?: string
  /** Shown on hover, without intercepting the click (e.g. so marker-click can navigate). */
  tooltipHtml?: string
  variant?: 'default' | 'user'
  draggable?: boolean
}

const { t } = useI18n()

const { center, zoom = 13, markers = [], fitToMarkers = false } = defineProps<{
  center: { lat: number, lng: number }
  zoom?: number
  markers?: IMapMarker[]
  fitToMarkers?: boolean
}>()

const emit = defineEmits<{
  'marker-dragend': [payload: { id: string, lat: number, lng: number }]
  'marker-click': [payload: { id: string }]
  'map-click': [payload: { lat: number, lng: number }]
}>()

const containerRef = useTemplateRef<HTMLDivElement>('container')
const mapRef = shallowRef<LeafletMap>()
const markerRefs = new Map<string, LeafletMarker>()
let leaflet: typeof import('leaflet') | null = null

function buildIcon(variant: 'default' | 'user' = 'default') {
  const colorClass = variant === 'user' ? 'bg-blue-500' : 'bg-red-500'
  return leaflet!.divIcon({
    className: '',
    html: `<div class="size-4 rounded-full border-2 border-white shadow-md ${colorClass}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  })
}

function renderMarkers(): void {
  if (!leaflet || !mapRef.value) return

  markerRefs.forEach(marker => marker.remove())
  markerRefs.clear()

  for (const markerData of markers) {
    const marker = leaflet.marker([markerData.lat, markerData.lng], {
      draggable: !!markerData.draggable,
      icon: buildIcon(markerData.variant),
    }).addTo(mapRef.value)

    if (markerData.popupHtml) marker.bindPopup(markerData.popupHtml)
    if (markerData.tooltipHtml) marker.bindTooltip(markerData.tooltipHtml, { direction: 'top', offset: [0, -8] })

    marker.on('click', () => emit('marker-click', { id: markerData.id }))
    marker.on('dragend', () => {
      const position = marker.getLatLng()
      emit('marker-dragend', { id: markerData.id, lat: position.lat, lng: position.lng })
    })

    markerRefs.set(markerData.id, marker)
  }
}

function fitBounds(): void {
  if (!leaflet || !mapRef.value || markers.length === 0) return
  const bounds = leaflet.latLngBounds(markers.map(marker => [marker.lat, marker.lng]))
  mapRef.value.fitBounds(bounds, { padding: [32, 32], maxZoom: 15 })
}

onMounted(async () => {
  if (!config.maps.enabled || !containerRef.value) return

  leaflet = await import('leaflet')
  await import('leaflet/dist/leaflet.css')

  const map = leaflet.map(containerRef.value).setView([center.lat, center.lng], zoom)
  leaflet.tileLayer(config.maps.tileUrl(config.maps.tileProviderKey), {
    attribution: config.maps.attribution,
    maxZoom: 19,
  }).addTo(map)

  map.on('click', (event) => {
    emit('map-click', { lat: event.latlng.lat, lng: event.latlng.lng })
  })

  mapRef.value = map
  renderMarkers()
  if (fitToMarkers) fitBounds()
})

onBeforeUnmount(() => {
  mapRef.value?.remove()
})

watch(() => markers, () => {
  renderMarkers()
  if (fitToMarkers) fitBounds()
}, { deep: true })

watch(() => center, (newCenter) => {
  mapRef.value?.setView([newCenter.lat, newCenter.lng])
})
</script>

<template>
  <div
    v-if="!config.maps.enabled"
    class="flex h-full min-h-48 items-center justify-center rounded-md border border-dashed bg-muted/30 p-4 text-center text-sm text-muted-foreground"
  >
    {{ t('congregations.map.unavailable') }}
  </div>
  <div v-else ref="container" class="size-full min-h-48 rounded-md" />
</template>
