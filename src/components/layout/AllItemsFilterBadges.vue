<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'

const { t } = useI18n()

const props = defineProps<{
  filterType: 'all' | 'containers' | 'items'
  hasImageFilter: 'all' | 'withImage' | 'withoutImage'
}>()

const emit = defineEmits<{
  'remove-filter-type': []
  'remove-filter': [filter: 'withImage' | 'withoutImage']
}>()

const activeFilters = computed<Array<{ key: string, label: string, type: 'filterType' | 'imageFilter' }>>(() => {
  const filters: Array<{ key: string, label: string, type: 'filterType' | 'imageFilter' }> = []
  
  // Filter type badge
  if (props.filterType !== 'all') {
    filters.push({
      key: props.filterType,
      label: t(`gear.allItems.filter.${props.filterType}`, props.filterType === 'containers' ? 'Containers' : 'Items'),
      type: 'filterType',
    })
  }
  
  // Image filter badges
  if (props.hasImageFilter === 'withImage') {
    filters.push({
      key: 'withImage',
      label: t('gear.allItems.filters.withImage', 'Only with image'),
      type: 'imageFilter',
    })
  }
  if (props.hasImageFilter === 'withoutImage') {
    filters.push({
      key: 'withoutImage',
      label: t('gear.allItems.filters.withoutImage', 'Only without image'),
      type: 'imageFilter',
    })
  }
  
  return filters
})

function removeFilter(filterKey: string, filterType: 'filterType' | 'imageFilter') {
  if (filterType === 'filterType') {
    emit('remove-filter-type')
  } else {
    emit('remove-filter', filterKey as 'withImage' | 'withoutImage')
  }
}
</script>

<template>
  <div v-if="activeFilters.length > 0" class="flex flex-wrap items-center gap-2">
    <Badge
      v-for="filter in activeFilters"
      :key="`${filter.type}-${filter.key}`"
      variant="secondary"
      class="flex items-center gap-1.5 pr-1"
    >
      <span>{{ filter.label }}</span>
      <Button
        variant="ghost"
        size="icon"
        class="size-4 h-auto w-auto p-0 hover:bg-transparent"
        @click="removeFilter(filter.key, filter.type)"
      >
        <X class="size-3" />
        <span class="sr-only">{{ t('gear.allItems.filters.removeFilter', 'Remove filter') }}</span>
      </Button>
    </Badge>
  </div>
</template>
