<script setup lang="ts">
import { FilterIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const { t } = useI18n()

const filterType = defineModel<'all' | 'containers' | 'items'>('filterType', {
  required: true,
})

const hasImageFilter = defineModel<'all' | 'withImage' | 'withoutImage'>('hasImageFilter', {
  required: true,
})

function handleFilterTypeChange(value: 'all' | 'containers' | 'items') {
  filterType.value = value
}

function handleImageFilterChange(value: 'all' | 'withImage' | 'withoutImage') {
  hasImageFilter.value = value
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="outline" size="icon" class="shrink-0">
        <FilterIcon class="size-4" />
        <span class="sr-only">{{ t('gear.allItems.filters.menu', 'More filters') }}</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem
        :data-selected="filterType === 'all' ? '' : undefined"
        @click="handleFilterTypeChange('all')"
      >
        {{ t('gear.allItems.filter.all', 'All') }}
      </DropdownMenuItem>
      <DropdownMenuItem
        :data-selected="filterType === 'containers' ? '' : undefined"
        @click="handleFilterTypeChange('containers')"
      >
        {{ t('gear.allItems.filter.containers', 'Containers') }}
      </DropdownMenuItem>
      <DropdownMenuItem
        :data-selected="filterType === 'items' ? '' : undefined"
        @click="handleFilterTypeChange('items')"
      >
        {{ t('gear.allItems.filter.items', 'Items') }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        :data-selected="hasImageFilter === 'withImage' ? '' : undefined"
        @click="handleImageFilterChange('withImage')"
      >
        {{ t('gear.allItems.filters.withImage', 'Only with image') }}
      </DropdownMenuItem>
      <DropdownMenuItem
        :data-selected="hasImageFilter === 'withoutImage' ? '' : undefined"
        @click="handleImageFilterChange('withoutImage')"
      >
        {{ t('gear.allItems.filters.withoutImage', 'Only without image') }}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
