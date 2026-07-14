<script setup lang="ts">
import { LayoutGrid, List } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { ButtonGroup } from '@/components/ui/button-group'
import Button from '@/components/ui/button/Button.vue'
import type { CongregationListViewMode } from '../types/congregationListView.types'

const { t } = useI18n()

const viewMode = defineModel<CongregationListViewMode>('viewMode', { required: true })
</script>

<template>
  <ButtonGroup role="group" :aria-label="t('congregations.list.view.toggleLabel')">
    <Button
      variant="outline"
      size="sm"
      :aria-pressed="viewMode === 'grid'"
      :class="viewMode === 'grid' ? 'bg-accent text-accent-foreground' : ''"
      @click="viewMode = 'grid'"
    >
      <LayoutGrid class="size-4" />
      <span class="hidden sm:inline">{{ t('congregations.list.view.grid') }}</span>
    </Button>
    <Button
      variant="outline"
      size="sm"
      :aria-pressed="viewMode === 'list'"
      :class="viewMode === 'list' ? 'bg-accent text-accent-foreground' : ''"
      @click="viewMode = 'list'"
    >
      <List class="size-4" />
      <span class="hidden sm:inline">{{ t('congregations.list.view.list') }}</span>
    </Button>
  </ButtonGroup>
</template>
