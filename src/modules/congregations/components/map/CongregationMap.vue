<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ICongregationDetail } from '../../types/congregation.types'
import type { IMapMarker } from './LeafletMapBase.vue'
import LeafletMapBase from './LeafletMapBase.vue'

const { t } = useI18n()

const { congregation } = defineProps<{
  congregation: ICongregationDetail
}>()

const hasCoordinates = computed<boolean>(
  () => congregation.latitude != null && congregation.longitude != null,
)

const center = computed<{ lat: number, lng: number }>(() => ({
  lat: congregation.latitude ?? 0,
  lng: congregation.longitude ?? 0,
}))

const markers = computed<IMapMarker[]>(() => hasCoordinates.value
  ? [{ id: congregation.id, lat: center.value.lat, lng: center.value.lng, popupHtml: congregation.name }]
  : [])

const googleMapsUrl = computed<string>(
  () => `https://www.google.com/maps?q=${center.value.lat},${center.value.lng}`,
)
</script>

<template>
  <div v-if="hasCoordinates" class="space-y-2">
    <div class="h-56 overflow-hidden rounded-md border">
      <LeafletMapBase :center :zoom="15" :markers />
    </div>
    <a
      :href="googleMapsUrl"
      target="_blank"
      rel="noopener"
      class="inline-flex items-center gap-1 text-sm text-primary hover:underline"
    >
      {{ t('congregations.detail.openInGoogleMaps') }}
    </a>
  </div>
</template>
