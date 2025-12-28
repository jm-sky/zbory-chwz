<script setup lang="ts">
import { Church } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useCongregations } from '../composables/useCongregations'

const { t } = useI18n()
const { data: congregations, isLoading, error } = useCongregations()
</script>

<template>
  <div class="space-y-4">
    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-3">
      <div
        v-for="i in 5"
        :key="i"
        class="h-20 animate-pulse rounded-lg bg-muted"
      />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center text-sm text-destructive">
      {{ t('congregations.list.error', 'Nie udało się załadować listy zborów') }}
    </div>

    <!-- Empty State -->
    <div v-else-if="!congregations || congregations.length === 0" class="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
      <Church class="mx-auto mb-2 size-8 opacity-50" />
      <p>{{ t('congregations.list.empty', 'Brak zborów do wyświetlenia') }}</p>
    </div>

    <!-- Congregations List -->
    <div v-else class="space-y-3">
      <div
        v-for="congregation in congregations"
        :key="congregation.id"
        class="flex items-start gap-4 rounded-lg border bg-card p-4 transition-colors hover:bg-accent/50"
      >
        <div class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Church class="size-5 text-primary" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-foreground">
            {{ congregation.name }}
          </h3>
          <p v-if="congregation.description" class="mt-1 text-sm text-muted-foreground line-clamp-2">
            {{ congregation.description }}
          </p>
          <div v-if="congregation.role && congregation.role.trim()" class="mt-2">
            <span class="inline-flex items-center rounded-full bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground">
              {{ congregation.role }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
