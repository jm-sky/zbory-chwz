<script setup lang="ts">
import { refDebounced } from '@vueuse/core'
import { History, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Pagination from '@/components/data-table/Pagination.vue'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import AiHistoryDetailDialog from '@/modules/ai/components/AiHistoryDetailDialog.vue'
import AiHistoryFilters from '@/modules/ai/components/AiHistoryFilters.vue'
import AiHistoryList from '@/modules/ai/components/AiHistoryList.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { AiOperationType } from '../types/chat'
import type { IAiHistoryItem } from '../types/history'
import { useAiChat } from '../composables/useAiChat'
import { useAiHistory } from '../composables/useAiHistory'
import { isAiOperationType } from '../utils/isAiOperationType.ts'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const { handleError } = useHandleError()

const { history, historyTotal, isLoading, loadHistory, deleteHistoryItem, clearHistory } = useAiHistory()
const { restoreFromHistory } = useAiChat()

// Search and pagination from URL (simple local implementation)
const search = computed({
  get: () => (route.query.search as string) || '',
  set: (value: string) => {
    const query = { ...route.query }
    if (value) {
      query.search = value
    } else {
      delete query.search
    }
    router.replace({ query })
  },
})

const page = computed({
  get: () => Number(route.query.page) || 1,
  set: (value: number) => {
    const query = { ...route.query }
    query.page = String(value)
    router.replace({ query })
  },
})

const pageSize = computed({
  get: () => Number(route.query.pageSize) || 20,
  set: (value: number) => {
    const query = { ...route.query }
    query.pageSize = String(value)
    router.replace({ query })
  },
})

const searchQueryRaw = ref(search.value)
const searchQuery = refDebounced(searchQueryRaw, 300)

// Operation type filter
const operationType = ref<AiOperationType | null>(
  isAiOperationType(route.query.operationType)
    ? route.query.operationType as AiOperationType
    : null,
)

// Dialog states
const isDeleteDialogOpen = ref(false)
const isDeleteAllDialogOpen = ref(false)
const isDetailDialogOpen = ref(false)
const selectedItem = ref<IAiHistoryItem | null>(null)
const itemToDelete = ref<string | null>(null)

// Computed
const total = computed(() => {
  // If searching client-side, return filtered count, otherwise use backend total
  if (searchQuery.value) {
    return filteredHistory.value.length
  }
  return historyTotal.value
})

// Load history when filters change
watch([searchQuery, operationType, page, pageSize], async () => {
  await loadHistoryData()
}, { immediate: false })

// Sync operationType with URL
watch(operationType, (newValue) => {
  const query = { ...route.query }
  if (newValue) {
    query.operationType = newValue
  } else {
    delete query.operationType
  }
  router.replace({ query })
})

// Sync searchQueryRaw with search
watch(search, (newValue) => {
  searchQueryRaw.value = newValue
})

// Load history data
const loadHistoryData = async (): Promise<void> => {
  try {
    const offset = (page.value - 1) * pageSize.value
    await loadHistory({
      limit: pageSize.value,
      offset,
      operationType: operationType.value ?? undefined,
    })

    // Filter by search query on frontend if backend doesn't support it
    // Note: Backend search is not implemented yet, so we filter client-side
    if (searchQuery.value) {
      // Filtering is done in computed property below
    }
  } catch (error) {
    handleError(error)
  }
}

// Filtered history based on search query (client-side filtering)
const filteredHistory = computed(() => {
  if (!searchQuery.value) {
    return history.value
  }

  const query = searchQuery.value.toLowerCase()
  return history.value.filter(item => {
    return item.finalPrompt.toLowerCase().includes(query)
      || (item.responseData && typeof item.responseData.message === 'string' && item.responseData.message.toLowerCase().includes(query))
      || item.model.toLowerCase().includes(query)
      || item.provider.toLowerCase().includes(query)
  })
})

// Handlers
const handleRestore = async (item: IAiHistoryItem): Promise<void> => {
  try {
    await restoreFromHistory(item)

    // Determine navigation target based on container_ids
    const containerIds = item.containerIds || (item.contextData ? Object.keys(item.contextData) : [])

    if (containerIds.length === 1) {
      // Single container - navigate to Container Detail Page
      router.push({
        path: `/gear/${containerIds[0]}`,
        query: { restoreHistoryId: item.id },
      })
    } else {
      // Multiple or no containers - navigate to Containers List Page
      router.push({
        path: '/gear',
        query: { restoreHistoryId: item.id },
      })
    }
  } catch (error) {
    handleError(error)
  }
}

const handleDelete = (id: string): void => {
  itemToDelete.value = id
  isDeleteDialogOpen.value = true
}

const handleDeleteConfirm = async (): Promise<void> => {
  if (!itemToDelete.value) return

  try {
    await deleteHistoryItem(itemToDelete.value)
    toast.success(t('ai.history.delete'))
    await loadHistoryData()
  } catch (error) {
    handleError(error)
  } finally {
    isDeleteDialogOpen.value = false
    itemToDelete.value = null
  }
}

const handleDeleteAll = (): void => {
  isDeleteAllDialogOpen.value = true
}

const handleDeleteAllConfirm = async (): Promise<void> => {
  try {
    await clearHistory()
    toast.success(t('ai.history.deleteAll'))
    await loadHistoryData()
  } catch (error) {
    handleError(error)
  } finally {
    isDeleteAllDialogOpen.value = false
  }
}

const handleViewDetails = (item: IAiHistoryItem): void => {
  selectedItem.value = item
  isDetailDialogOpen.value = true
}

const handleClearFilters = (): void => {
  searchQueryRaw.value = ''
  operationType.value = null
}

// Load on mount
onMounted(async () => {
  await loadHistoryData()
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="w-full max-w-full space-y-6">
      <!-- Header -->
      <CommonPageHeader :icon="History" :label="t('ai.history.title')">
        <template #actions>
          <Button
            variant="destructive"
            size="sm"
            :disabled="history.length === 0 || isLoading"
            @click="handleDeleteAll"
          >
            <Trash2 class="size-4" />
            {{ t('ai.history.deleteAll') }}
          </Button>
        </template>
      </CommonPageHeader>

      <!-- Filters -->
      <AiHistoryFilters
        v-model:search-query="searchQueryRaw"
        v-model:operation-type="operationType"
        :loading="isLoading"
        @clear-filters="handleClearFilters"
        @refresh="loadHistoryData"
      />

      <!-- History List -->
      <AiHistoryList
        :items="filteredHistory"
        :loading="isLoading"
        @restore="handleRestore"
        @delete="handleDelete"
        @view-details="handleViewDetails"
      />

      <!-- Pagination -->
      <Pagination
        v-if="total > 0 && !searchQuery"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
      />

      <!-- Delete Confirmation Dialog -->
      <Dialog :open="isDeleteDialogOpen" @update:open="(open) => { isDeleteDialogOpen = open }">
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {{ t('ai.history.delete') }}
            </DialogTitle>
            <DialogDescription>
              {{ t('ai.history.confirmDelete') }}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" @click="isDeleteDialogOpen = false">
              {{ t('common.cancel') }}
            </Button>
            <Button variant="destructive" @click="handleDeleteConfirm">
              {{ t('common.delete') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- Delete All Confirmation Dialog -->
      <Dialog :open="isDeleteAllDialogOpen" @update:open="(open) => { isDeleteAllDialogOpen = open }">
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {{ t('ai.history.deleteAll') }}
            </DialogTitle>
            <DialogDescription>
              {{ t('ai.history.confirmDeleteAll') }}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" @click="isDeleteAllDialogOpen = false">
              {{ t('common.cancel') }}
            </Button>
            <Button variant="destructive" @click="handleDeleteAllConfirm">
              {{ t('common.delete') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- Detail Dialog -->
      <AiHistoryDetailDialog
        v-model:open="isDetailDialogOpen"
        :item="selectedItem"
        @restore="handleRestore"
        @delete="handleDelete"
      />
    </div>
  </AuthenticatedLayout>
</template>

