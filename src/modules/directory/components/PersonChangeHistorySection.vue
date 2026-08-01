<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pagination } from '@/components/data-table'
import { logSafeError } from '@/shared/utils/logSafeError'
import type { IPersonChangeLogBatch } from '../types/directory.types'
import { directoryApiService } from '../services/directoryApiService'

const { personId } = defineProps<{ personId: string }>()

const { t } = useI18n()

const loading = ref(true)
// null while unresolved/loading; empty array once loaded means "visible but no history yet".
// The section renders nothing at all if the endpoint returned 403 (not authorized to view).
const batches = ref<IPersonChangeLogBatch[] | null>(null)
const visible = ref(false)
const page = ref<number>(1)
const pageSize = ref<number>(10)
const total = ref<number>(0)

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString()
}

async function load() {
  loading.value = true
  try {
    const skip = (page.value - 1) * pageSize.value
    const response = await directoryApiService.getChangeLog(personId, { skip, limit: pageSize.value })
    if (response === null) {
      visible.value = false
      return
    }
    visible.value = true
    batches.value = response.batches
    total.value = response.total
  } catch (error) {
    logSafeError('Failed to load person change history:', error)
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
  <div v-if="visible" class="space-y-3">
    <h4 class="text-sm font-semibold">
      {{ t('directory.changeHistory.title', 'Historia zmian') }}
    </h4>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>
    <p v-else-if="!batches || batches.length === 0" class="text-sm text-muted-foreground">
      {{ t('directory.changeHistory.empty', 'Brak zarejestrowanych zmian') }}
    </p>

    <template v-else>
      <ul class="space-y-2">
        <li
          v-for="batch in batches"
          :key="batch.batch_id"
          class="flex flex-col gap-2 rounded-md border px-3 py-2 text-sm"
        >
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
          <p class="text-xs text-muted-foreground">
            {{ batch.actor_label }} · {{ formatCreatedAt(batch.created_at) }}
          </p>
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
