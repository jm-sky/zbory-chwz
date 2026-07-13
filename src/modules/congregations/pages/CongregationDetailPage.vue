<script setup lang="ts">
import { Church, Clock, Mail, MapPin, Pencil, Phone, User } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { getErrorStatus } from '@/shared/utils/errorGuards'
import type { ICongregationDetail } from '../types/congregation.types'
import { useCongregationDetail } from '../composables/useCongregationDetail'
import { CongregationRoutePaths } from '../routes'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const congregationId = computed<string>(() => route.params.id as string)
const { data: congregation, isLoading, isError, error } = useCongregationDetail(congregationId)

const notFound = computed<boolean>(() => getErrorStatus(error.value) === 404)

function formatAddress(item: ICongregationDetail): string {
  const parts: string[] = []
  if (item.street) parts.push(item.street)
  if (item.postal_code && item.city) {
    parts.push(`${item.postal_code} ${item.city}`)
  } else if (item.city) {
    parts.push(item.city)
  }
  return parts.join(', ')
}

function formatServiceTimes(item: ICongregationDetail): string {
  return item.service_times
    .map((st) => st.description ? `${st.day} ${st.time} - ${st.description}` : `${st.day} ${st.time}`)
    .join(', ')
}
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
        @back="router.push(CongregationRoutePaths.list)"
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
            :to="CongregationRoutePaths.editById(congregation.id)"
            size="sm"
            :aria-label="t('congregations.detail.edit')"
          >
            <Pencil class="size-4" />
            <span class="hidden sm:inline">{{ t('congregations.detail.edit') }}</span>
          </ButtonLink>
        </template>
      </CommonPageHeader>

      <div class="space-y-6 pb-4 sm:pb-6">
        <!-- Address -->
        <div v-if="formatAddress(congregation)">
          <div class="flex items-center gap-3">
            <MapPin class="size-5 shrink-0 text-muted-foreground" />
            <h3 class="text-sm font-medium text-muted-foreground">
              {{ t('congregations.detail.address') }}
            </h3>
          </div>
          <p class="mt-1 pl-8 text-foreground">
            {{ formatAddress(congregation) }}
          </p>
        </div>

        <!-- Service Times -->
        <div v-if="congregation.service_times.length > 0">
          <div class="flex items-center gap-3">
            <Clock class="size-5 shrink-0 text-muted-foreground" />
            <h3 class="text-sm font-medium text-muted-foreground">
              {{ t('congregations.detail.serviceTimes') }}
            </h3>
          </div>
          <p class="mt-1 pl-8 text-foreground">
            {{ formatServiceTimes(congregation) }}
          </p>
        </div>

        <!-- Contacts -->
        <div v-if="congregation.card_contacts.length > 0">
          <div class="flex items-center gap-3">
            <User class="size-5 shrink-0 text-muted-foreground" />
            <h3 class="text-sm font-medium text-muted-foreground">
              {{ t('congregations.detail.contacts') }}
            </h3>
          </div>
          <div class="mt-2 space-y-4 pl-8">
            <div
              v-for="(contact, contactIndex) in congregation.card_contacts"
              :key="`contact-${contactIndex}`"
              class="space-y-1"
            >
              <div>
                <span class="font-medium text-foreground">{{ contact.name }}</span>
                <span v-if="contact.title" class="text-muted-foreground">
                  {{ ` - ${contact.title}` }}
                </span>
              </div>
              <p v-if="contact.description" class="text-sm text-muted-foreground">
                {{ contact.description }}
              </p>
              <div v-if="contact.phone || contact.email" class="space-y-1">
                <a
                  v-if="contact.phone"
                  :href="`tel:${contact.phone}`"
                  class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Phone class="size-3.5" />
                  <span>{{ contact.phone }}</span>
                </a>
                <a
                  v-if="contact.email"
                  :href="`mailto:${contact.email}`"
                  class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Mail class="size-3.5" />
                  <span class="break-all">{{ contact.email }}</span>
                </a>
              </div>
            </div>
          </div>
        </div>

        <!-- Hidden contacts (editors only) -->
        <div v-if="congregation.hidden_contacts?.length">
          <div class="flex items-center gap-3 opacity-60">
            <User class="size-5 shrink-0 text-muted-foreground" />
            <h3 class="text-sm font-medium text-muted-foreground">
              {{ t('congregations.detail.hiddenContacts') }}
            </h3>
          </div>
          <div class="mt-2 space-y-4 pl-8 opacity-60">
            <div
              v-for="(contact, contactIndex) in congregation.hidden_contacts"
              :key="`hidden-contact-${contactIndex}`"
              class="space-y-1"
            >
              <div>
                <span class="font-medium text-foreground">{{ contact.name }}</span>
                <span v-if="contact.title" class="text-muted-foreground">
                  {{ ` - ${contact.title}` }}
                </span>
              </div>
              <p v-if="contact.description" class="text-sm text-muted-foreground">
                {{ contact.description }}
              </p>
              <div v-if="contact.phone || contact.email" class="space-y-1">
                <a
                  v-if="contact.phone"
                  :href="`tel:${contact.phone}`"
                  class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Phone class="size-3.5" />
                  <span>{{ contact.phone }}</span>
                </a>
                <a
                  v-if="contact.email"
                  :href="`mailto:${contact.email}`"
                  class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Mail class="size-3.5" />
                  <span class="break-all">{{ contact.email }}</span>
                </a>
              </div>
            </div>
          </div>
        </div>

        <!-- Branches -->
        <div v-if="congregation.branches.length > 0">
          <h3 class="mb-2 text-sm font-medium text-muted-foreground">
            {{ t('congregations.detail.branches') }}
          </h3>
          <div class="flex flex-wrap gap-2">
            <Badge v-for="branch in congregation.branches" :key="branch.id" variant="secondary">
              {{ branch.name }}
            </Badge>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>
