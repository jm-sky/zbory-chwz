<script setup lang="ts">
import { Braces, Download, FileText } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { ICongregationDetailed } from '../types/congregation.types'
import type { ExportFormat } from '../utils/exportCongregations'
import { useCongregationExport } from '../composables/useCongregationExport'

const { t } = useI18n()
const { exportCongregations } = useCongregationExport()

const { congregations } = defineProps<{ congregations: ICongregationDetailed[] }>()

function handleExport(format: ExportFormat): void {
  exportCongregations(congregations, format)
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        :disabled="congregations.length === 0"
      >
        <Download class="size-4" />
        {{ t('congregations.export.button') }}
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem @click="handleExport('json')">
        <Braces class="size-4" />
        <span>{{ t('congregations.export.json') }}</span>
      </DropdownMenuItem>
      <DropdownMenuItem @click="handleExport('markdown')">
        <FileText class="size-4" />
        <span>{{ t('congregations.export.markdown') }}</span>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
