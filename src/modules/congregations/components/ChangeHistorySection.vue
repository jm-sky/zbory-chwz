<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IChangeLogEntry } from '../types/congregation.types'
import { congregationApiService } from '../services/congregationApiService'

const { tenantId } = defineProps<{ tenantId: string }>()

const { t } = useI18n()
const { handleError } = useHandleError()

const loading = ref(true)
// null while unresolved/loading; empty array once loaded means "visible but no history yet".
// The section renders nothing at all if the endpoint returned 403 (not authorized to view).
const entries = ref<IChangeLogEntry[] | null>(null)
const visible = ref(false)

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
    const response = await congregationApiService.getChangeLog(tenantId)
    if (response === null) {
      visible.value = false
      return
    }
    visible.value = true
    entries.value = response.entries
  } catch (error) {
    handleError(error, { fallbackMessage: t('congregations.changeHistory.loadError', 'Nie udało się pobrać historii zmian') })
  } finally {
    loading.value = false
  }
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
    <p v-else-if="!entries || entries.length === 0" class="text-sm text-muted-foreground">
      {{ t('congregations.changeHistory.empty', 'Brak zarejestrowanych zmian') }}
    </p>

    <ul v-else class="space-y-2">
      <li
        v-for="entry in entries"
        :key="entry.id"
        class="flex flex-col gap-1 rounded-md border px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium">{{ entry.field_label }}</span>
            <Badge variant="outline">
              {{ sourceLabel(entry.source) }}
            </Badge>
          </div>
          <p class="text-muted-foreground">
            <span v-if="entry.old_value" class="line-through">{{ entry.old_value }}</span>
            <span v-if="entry.old_value"> → </span>
            <span>{{ entry.new_value ?? '—' }}</span>
          </p>
          <p class="text-xs text-muted-foreground">
            {{ entry.actor_label }} · {{ formatCreatedAt(entry.created_at) }}
          </p>
        </div>
      </li>
    </ul>
  </div>
</template>
