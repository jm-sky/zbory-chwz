<script setup lang="ts">
import { Church, Pencil } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { getErrorStatus } from '@/shared/utils/errorGuards'
import ChangeHistorySection from '../components/ChangeHistorySection.vue'
import CongregationCompletenessIndicator from '../components/CongregationCompletenessIndicator.vue'
import CongregationDetailContent from '../components/CongregationDetailContent.vue'
import { useCongregationDetail } from '../composables/useCongregationDetail'
import { CongregationRoutePaths } from '../routes'
import { calculateCongregationCompletenessFromDetail } from '../utils/congregationCompleteness'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const congregationId = computed<string>(() => route.params.id as string)
const { data: congregation, isLoading, isError, error } = useCongregationDetail(congregationId)

const notFound = computed<boolean>(() => getErrorStatus(error.value) === 404)
const isAdmin = computed<boolean>(() => !!(authStore.user?.isAdmin || authStore.user?.isOwner))
const completeness = computed(() =>
  congregation.value ? calculateCongregationCompletenessFromDetail(congregation.value) : null,
)
</script>

<template>
  <MainLayout>
    <div v-if="isLoading" class="space-y-6">
      <div class="h-32 animate-pulse rounded-lg bg-muted" />
    </div>

    <div v-else-if="isError" class="space-y-6">
      <div class="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center text-destructive">
        <Church class="mx-auto mb-4 size-12 opacity-50" />
        <h2 class="mb-2 text-xl font-semibold">
          {{ notFound ? t('congregations.detail.notFoundTitle') : t('congregations.detail.errorTitle') }}
        </h2>
        <p v-if="notFound">
          {{ t('congregations.detail.notFound') }}
        </p>
        <p v-else>
          {{ t('congregations.detail.error') }}
        </p>
      </div>
    </div>

    <div v-else-if="congregation" class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="Church"
        :label="congregation.name"
        with-back-button
        @back="router.push({ path: CongregationRoutePaths.list, query: route.query })"
      >
        <template #description>
          <div class="flex items-center gap-2 flex-wrap">
            <Badge
              v-if="congregation.status === 'draft'"
              variant="outline"
              class="border-dashed text-muted-foreground border-muted-foreground/50"
            >
              {{ t('congregations.status.draft') }}
            </Badge>
            <Badge
              v-else-if="congregation.status === 'published_unverified'"
              variant="outline"
              class="opacity-60 text-muted-foreground border-muted-foreground/50"
            >
              {{ t('congregations.status.unverified') }}
            </Badge>
            <span v-if="congregation.description">{{ congregation.description }}</span>
          </div>
        </template>
        <template v-if="congregation.canManage" #actions>
          <ButtonLink
            :to="{ path: CongregationRoutePaths.editById(congregation.id), query: { from: 'detail' } }"
            size="sm"
            :aria-label="t('congregations.detail.edit')"
          >
            <Pencil class="size-4" />
            <span class="hidden sm:inline">{{ t('congregations.detail.edit') }}</span>
          </ButtonLink>
        </template>
      </CommonPageHeader>

      <CongregationCompletenessIndicator
        v-if="isAdmin && completeness"
        :score="completeness.score"
        :missing-fields="completeness.missingFields"
      />

      <CongregationDetailContent :congregation="congregation" />

      <ChangeHistorySection
        v-if="congregation.canManage"
        :tenant-id="congregation.id"
      />
    </div>
  </MainLayout>
</template>
