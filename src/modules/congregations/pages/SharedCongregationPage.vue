<script setup lang="ts">
import { Church } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import LogoText from '@/components/ui/LogoText.vue'
import PublicLayout from '@/layouts/PublicLayout.vue'
import CongregationDetailContent from '../components/CongregationDetailContent.vue'
import { useSharedCongregation } from '../composables/useSharedCongregation'

const { t } = useI18n()
const route = useRoute()

const token = computed<string>(() => route.params.token as string)
const { data: congregation, isLoading, isError } = useSharedCongregation(token)
</script>

<template>
  <PublicLayout>
    <div class="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8">
      <div v-if="isLoading" class="space-y-6">
        <div class="h-32 animate-pulse rounded-lg bg-muted" />
      </div>

      <div v-else-if="isError" class="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center text-destructive">
        <Church class="mx-auto mb-4 size-12 opacity-50" />
        <h2 class="mb-2 text-xl font-semibold">
          {{ t('congregations.sharedView.invalidTitle') }}
        </h2>
        <p>{{ t('congregations.sharedView.invalid') }}</p>
      </div>

      <div v-else-if="congregation" class="space-y-6">
        <div class="flex items-center gap-4">
          <div class="flex size-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Church class="size-6 text-primary" />
          </div>
          <div>
            <h1 class="text-2xl font-semibold text-foreground">
              {{ congregation.name }}
            </h1>
            <p v-if="congregation.description" class="text-sm text-muted-foreground">
              {{ congregation.description }}
            </p>
          </div>
        </div>

        <CongregationDetailContent :congregation="congregation" />

        <p class="flex items-center gap-1 text-xs text-muted-foreground">
          {{ t('congregations.sharedView.poweredBy') }}
          <LogoText class="text-xs" />
        </p>
      </div>
    </div>
  </PublicLayout>
</template>
