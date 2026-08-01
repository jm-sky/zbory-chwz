<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pagination } from '@/components/data-table'
import { Badge } from '@/components/ui/badge'
import { logSafeError } from '@/shared/utils/logSafeError'
import type { IChangeLogBatch } from '../types/congregation.types'
import { congregationApiService } from '../services/congregationApiService'

const { tenantId } = defineProps<{ tenantId: string }>()

const { t } = useI18n()

const loading = ref(true)
// null while unresolved/loading; empty array once loaded means "visible but no history yet".
// The section renders nothing at all if the endpoint returned 403 (not authorized to view).
const batches = ref<IChangeLogBatch[] | null>(null)
const visible = ref(false)
const page = ref<number>(1)
const pageSize = ref<number>(10)
const total = ref<number>(0)

const SOURCE_LABELS: Record<string, string> = {
  admin_manual: 'Edycja ręczna',
  import_paste: 'Import z tekstu',
  email_auto: 'E-mail (automatycznie)',
  email_reviewed: 'E-mail (zatwierdzone ręcznie)',
}

function sourceLabel(source: string): string {
  return t(`congregations.changeHistory.source.${source}`, SOURCE_LABELS[source] ?? source)
}

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString()
}

async function load() {
  loading.value = true
  try {
    const skip = (page.value - 1) * pageSize.value
    const response = await congregationApiService.getChangeLog(tenantId, { skip, limit: pageSize.value })
    if (response === null) {
      // 403 / not allowed — hide quietly (no toast; history is optional UI)
      visible.value = false
      return
    }
    visible.value = true
    batches.value = response.batches
    total.value = response.total
  } catch (error) {
    // Secondary section: fail closed without a red toast (empty/unavailable ≠ critical)
    logSafeError('Failed to load congregation change history:', error)
    visible.value = false
    batches.value = null
  } finally {
    loading.value = false
  }
}

function onPageChange(newPage: number) {
  page.value = newPage
  load()
}

function onPageSizeChange(newSize: number) {
  pageSize.value = newSize
}

onMounted(load)
</script>

<template>
  <div v-if="visible" class="space-y-4 rounded-lg border p-4">
    <h3 class="text-lg font-semibold">
      {{ t('congregations.changeHistory.title', 'Historia zmian') }}
    </h3>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>
    <p v-else-if="!batches || batches.length === 0" class="text-sm text-muted-foreground">
      {{ t('congregations.changeHistory.empty', 'Brak zarejestrowanych zmian') }}
    </p>

    <template v-else>
      <ul class="space-y-2">
        <li
          v-for="batch in batches"
          :key="batch.batch_id"
          class="flex flex-col gap-2 rounded-md border px-3 py-2 text-sm"
        >
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="outline">
              {{ sourceLabel(batch.source) }}
            </Badge>
            <span class="text-xs text-muted-foreground">
              {{ batch.actor_label }} · {{ formatCreatedAt(batch.created_at) }}
            </span>
          </div>
          <ul class="space-y-1">
            <li v-for="change in batch.changes" :key="change.id">
              <span class="font-medium">{{ change.field_label }}</span>
              <p class="text-muted-foreground">
                <span v-if="change.old_value" class="line-through">{{ change.old_value }}</span>
                <span v-if="change.old_value"> → </span>
                <span>{{ change.new_value ?? '—' }}</span>
              </p>
            </li>
          </ul>
        </li>
      </ul>

      <Pagination
        :page
        :page-size="pageSize"
        :total
        :page-size-options="[10, 20, 50, 100]"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </template>
  </div>
</template>
