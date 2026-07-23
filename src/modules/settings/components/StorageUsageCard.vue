<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { HardDrive } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { apiClient } from '@/shared/services/apiClient'

interface StorageUsageResponse {
  usedBytes: number
  limitBytes: number
  usedPercentage: number
}

const { t } = useI18n()

const { data: storageUsage, isLoading } = useQuery<StorageUsageResponse>({
  queryKey: ['storage', 'usage'],
  queryFn: async () => {
    const response = await apiClient.get<StorageUsageResponse>('/users/me/storage/usage')
    return response.data
  },
  staleTime: 5 * 60 * 1000, // 5 minutes
})

const formattedUsed = computed(() => {
  if (!storageUsage.value) return '0 B'
  return formatBytes(storageUsage.value.usedBytes)
})

const formattedLimit = computed(() => {
  if (!storageUsage.value) return '0 B'
  return formatBytes(storageUsage.value.limitBytes)
})

const progressPercentage = computed(() => {
  if (!storageUsage.value) return 0
  return Math.min(storageUsage.value.usedPercentage, 100)
})

const progressColor = computed(() => {
  const percentage = progressPercentage.value
  if (percentage >= 90) return 'bg-red-500'
  if (percentage >= 70) return 'bg-yellow-500'
  return 'bg-green-500'
})

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <HardDrive :size="20" />
        <CardTitle>{{ t('settings.storage.title') }}</CardTitle>
      </div>
      <CardDescription>{{ t('settings.storage.description') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="isLoading" class="space-y-4">
        <div class="h-4 w-3/4 bg-muted rounded animate-pulse" />
        <div class="h-2 w-full bg-muted rounded animate-pulse" />
      </div>

      <div v-else-if="storageUsage" class="space-y-4">
        <!-- Usage Info -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">{{ t('settings.storage.used') }}</span>
            <span class="font-medium">
              {{ formattedUsed }} / {{ formattedLimit }}
            </span>
          </div>

          <!-- Progress Bar -->
          <div class="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              :class="progressColor"
              class="h-full transition-all duration-300"
              :style="{ width: `${progressPercentage}%` }"
            />
          </div>

          <!-- Percentage -->
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span>{{ t('settings.storage.usagePercentage') }}</span>
            <span>{{ progressPercentage.toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <div v-else class="text-sm text-muted-foreground">
        {{ t('settings.storage.error') }}
      </div>
    </CardContent>
  </Card>
</template>

