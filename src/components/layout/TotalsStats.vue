<script setup lang="ts">
import { Users } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { statsService } from '@/modules/stats/services/statsService'

const { t } = useI18n()

// Stats state
const totalUsers = ref(0)
const newUsersThisMonth = ref(0)
const loading = ref(true)

// Fetch stats using statsService
const fetchStats = async () => {
  try {
    const service = statsService()
    const stats = await service.getAllStats()

    totalUsers.value = stats.users.total
    newUsersThisMonth.value = stats.users.newThisMonth
  } catch (error) {
    console.error('Error fetching stats:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<template>
  <div class="grid grid-cols-1 gap-4">
    <!-- Total Users -->
    <div class="bg-card/50 backdrop-blur-sm rounded-lg border p-6 text-center">
      <div class="flex justify-center mb-3">
        <div class="rounded-full bg-primary/10 p-3">
          <Users class="size-6 text-primary" />
        </div>
      </div>
      <div class="text-3xl font-bold text-primary mb-1">
        {{ loading ? '...' : totalUsers.toLocaleString() }}
      </div>
      <div class="text-sm text-muted-foreground mb-2">
        {{ t('landing.stats.totalUsers', 'Total Users') }}
      </div>
      <div v-if="!loading && newUsersThisMonth > 0" class="text-xs text-muted-foreground">
        +{{ newUsersThisMonth }} {{ t('landing.stats.newThisMonth', 'this month') }}
      </div>
    </div>
  </div>
</template>
