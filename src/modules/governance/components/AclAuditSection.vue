<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pagination } from '@/components/data-table'
import { Badge } from '@/components/ui/badge'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IAclAuditBatch } from '../types/governance.types'
import { governanceApiService } from '../services/governanceApiService'

const { scopeType, scopeId } = defineProps<{
  scopeType: string
  scopeId: string
}>()

const { t } = useI18n()
const { handleError } = useHandleError()

const loading = ref(true)
const batches = ref<IAclAuditBatch[]>([])
const page = ref<number>(1)
const pageSize = ref<number>(10)
const total = ref<number>(0)

function actionLabel(action: string): string {
  return t(`governance.audit.action.${action}`, action)
}

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString()
}

function entrySummary(entry: IAclAuditBatch['entries'][number]): string {
  const parts = [actionLabel(entry.action)]
  if (entry.roleName) parts.push(t(`congregations.people.roles.${entry.roleName}`, entry.roleName))
  if (entry.permission) parts.push(entry.permission)
  if (entry.effect) parts.push(t(`governance.permissions.state.${entry.effect}`, entry.effect))
  return parts.join(' · ')
}

async function load() {
  loading.value = true
  try {
    const skip = (page.value - 1) * pageSize.value
    const response = await governanceApiService.listAuditLog(scopeType, scopeId, { skip, limit: pageSize.value })
    batches.value = response.batches
    total.value = response.total
  } catch (error) {
    handleError(error, { fallbackMessage: t('governance.audit.loadError', 'Nie udało się pobrać dziennika audytu') })
  } finally {
    loading.value = false
  }
}

function onPageChange(newPage: number) {
  page.value = newPage
  void load()
}

function onPageSizeChange(newSize: number) {
  pageSize.value = newSize
}

watch(() => [scopeType, scopeId], () => {
  page.value = 1
  void load()
}, { immediate: true })
</script>

<template>
  <div class="space-y-4 rounded-lg border p-4">
    <h3 class="text-lg font-semibold">
      {{ t('governance.audit.title', 'Dziennik audytu') }}
    </h3>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>
    <p v-else-if="batches.length === 0" class="text-sm text-muted-foreground">
      {{ t('governance.audit.empty', 'Brak zarejestrowanych zdarzeń') }}
    </p>

    <template v-else>
      <ul class="space-y-2">
        <li
          v-for="batch in batches"
          :key="batch.batchId"
          class="flex flex-col gap-2 rounded-md border px-3 py-2 text-sm"
        >
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="outline">
              {{ batch.actorLabel }}
            </Badge>
            <span class="text-xs text-muted-foreground">
              {{ formatCreatedAt(batch.createdAt) }}
            </span>
          </div>
          <ul class="space-y-1">
            <li v-for="entry in batch.entries" :key="entry.id">
              <span class="font-medium">{{ entry.targetLabel }}</span>
              <span class="text-muted-foreground"> — {{ entrySummary(entry) }}</span>
              <span v-if="entry.scopeType" class="text-xs text-muted-foreground">
                ({{ t(`governance.roles.scopeType.${entry.scopeType}`, entry.scopeType) }})
              </span>
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
