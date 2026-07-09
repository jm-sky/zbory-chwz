<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Church, Clock, Edit, EyeOff, Mail, MapPin, MoreHorizontal, Phone, Search, User } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import SearchInput from '@/components/ui/input/SearchInput.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { ICongregationDetailed, ICardContact } from '../types/congregation.types'
import { useCongregations } from '../composables/useCongregations'
import { CongregationRoutePaths } from '../routes'
import { congregationApiService } from '../services/congregationApiService'

const { t } = useI18n()
const router = useRouter()
const queryClient = useQueryClient()
const authStore = useAuthStore()
const { handleError } = useHandleError()
const { data: congregations, isLoading, error } = useCongregations()

const searchQuery = ref<string>('')

const filteredCongregations = computed<ICongregationDetailed[]>(() => {
  const items = congregations.value ?? []
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return items

  return items.filter((congregation) => {
    const cardContactsText = getCardContacts(congregation)
      .map(formatCardContactSearchText)
      .join(' ')
    const haystack = [
      congregation.name,
      congregation.description,
      congregation.city,
      congregation.street,
      congregation.postal_code,
      congregation.contact_name,
      cardContactsText,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return haystack.includes(query)
  })
})

function getCardContacts(congregation: ICongregationDetailed): ICardContact[] {
  if (congregation.card_contacts?.length) {
    return congregation.card_contacts.filter(contact => contact.name)
  }
  if (congregation.contact_name) {
    return [{
      name: congregation.contact_name,
      title: congregation.contact_title,
      phone: congregation.contact_phone,
      email: congregation.contact_email,
    }]
  }
  return []
}

function formatCardContactSearchText(contact: ICardContact): string {
  return [contact.name, contact.title, contact.phone, contact.email]
    .filter(Boolean)
    .join(' ')
}

// Check if user can edit/unpublish a congregation
function canManageCongregation(congregation: ICongregationDetailed): boolean {
  // Admin or owner can manage any congregation
  if (authStore.user?.isAdmin || authStore.user?.isOwner) {
    return true
  }
  // Tenant user (has role for this congregation)
  return !!congregation.role
}

function formatAddress(congregation: NonNullable<typeof congregations.value>[0]): string {
  const parts: string[] = []
  if (congregation.street) parts.push(congregation.street)
  if (congregation.postal_code && congregation.city) {
    parts.push(`${congregation.postal_code} ${congregation.city}`)
  } else if (congregation.city) {
    parts.push(congregation.city)
  }
  return parts.join(', ') || ''
}

function formatServiceTimes(serviceTimes?: Array<{ day: string; time: string }>): string {
  if (!serviceTimes || serviceTimes.length === 0) return ''
  return serviceTimes.map((st) => `${st.day} ${st.time}`).join(', ')
}

async function handleEdit(congregation: ICongregationDetailed) {
  router.push(CongregationRoutePaths.editById(congregation.id))
}

async function handleUnpublish(congregation: ICongregationDetailed) {
  if (!confirm(t('congregations.list.unpublishConfirm', 'Czy na pewno chcesz cofnąć publikację tego zboru?'))) {
    return
  }

  try {
    await congregationApiService.unpublishCongregation(congregation.id)
    toast.success(t('congregations.list.unpublishSuccess', 'Zbór został cofnięty z publikacji'))
    // Invalidate and refetch congregations
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
  } catch (error) {
    console.error('Failed to unpublish congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.list.unpublishError', 'Nie udało się cofnąć publikacji zboru') })
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Search -->
    <SearchInput
      v-if="!isLoading && !error && congregations && congregations.length > 0"
      id="congregations-search"
      v-model="searchQuery"
      name="congregations-search"
      :placeholder="t('congregations.list.searchPlaceholder', 'Szukaj zborów...')"
    />

    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-3">
      <div
        v-for="i in 5"
        :key="i"
        class="h-32 animate-pulse rounded-lg bg-muted"
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

    <!-- No Search Results -->
    <div v-else-if="filteredCongregations.length === 0" class="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
      <Search class="mx-auto mb-2 size-8 opacity-50" />
      <p>{{ t('congregations.list.noResults', 'Brak wyników dla podanej frazy') }}</p>
    </div>

    <!-- Congregations List -->
    <div v-else class="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
      <div
        v-for="congregation in filteredCongregations"
        :key="congregation.id"
        :class="[
          'group rounded-lg border p-6 transition-all hover:shadow-md',
          congregation.status === 'published_unverified'
            ? 'bg-muted/30 border-muted-foreground/20 hover:border-muted-foreground/40 opacity-90'
            : 'bg-card hover:border-primary/50'
        ]"
      >
        <!-- Header -->
        <div class="mb-4 flex items-start gap-4">
          <div class="flex size-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
            <Church class="size-6 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <h3
                :class="[
                  'text-lg font-semibold leading-tight',
                  congregation.status === 'published_unverified' ? 'text-muted-foreground' : 'text-foreground'
                ]"
              >
                {{ congregation.name }}
              </h3>
              <Badge
                v-if="congregation.status === 'published_unverified'"
                variant="outline"
                class="opacity-60 text-muted-foreground border-muted-foreground/50"
              >
                {{ t('congregations.status.unverified', 'Draft') }}
              </Badge>
            </div>
            <p
              v-if="congregation.description"
              :class="[
                'mt-1 text-sm line-clamp-2',
                congregation.status === 'published_unverified' ? 'text-muted-foreground/70' : 'text-muted-foreground'
              ]"
            >
              {{ congregation.description }}
            </p>
          </div>
          <!-- Actions Dropdown -->
          <DropdownMenu v-if="canManageCongregation(congregation)">
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="shrink-0">
                <MoreHorizontal class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="handleEdit(congregation)">
                <Edit class="size-4" />
                <span>{{ t('common.edit', 'Edytuj') }}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                v-if="congregation.status === 'published' || congregation.status === 'published_unverified'"
                @click="handleUnpublish(congregation)"
              >
                <EyeOff class="size-4" />
                <span>{{ t('congregations.list.unpublish', 'Cofnij publikację') }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <!-- Details Grid -->
        <div class="space-y-3">
          <!-- Address -->
          <div v-if="formatAddress(congregation)" class="flex items-start gap-2 text-sm">
            <MapPin class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="text-muted-foreground">{{ formatAddress(congregation) }}</span>
          </div>

          <!-- Service Times -->
          <div v-if="formatServiceTimes(congregation.service_times)" class="flex items-start gap-2 text-sm">
            <Clock class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="text-muted-foreground">{{ formatServiceTimes(congregation.service_times) }}</span>
          </div>

          <!-- Card contacts -->
          <div
            v-for="(contact, contactIndex) in getCardContacts(congregation)"
            :key="`${congregation.id}-contact-${contactIndex}`"
            class="space-y-1.5"
          >
            <div class="flex items-start gap-2 text-sm">
              <User class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div class="min-w-0 flex-1">
                <span class="font-medium text-foreground">{{ contact.name }}</span>
                <span v-if="contact.title" class="text-muted-foreground">
                  {{ ` - ${contact.title}` }}
                </span>
              </div>
            </div>
            <div
              v-if="contact.phone || contact.email"
              class="ml-6 space-y-1.5 text-sm"
            >
              <a
                v-if="contact.phone"
                :href="`tel:${contact.phone}`"
                class="flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <Phone class="size-3.5" />
                <span>{{ contact.phone }}</span>
              </a>
              <a
                v-if="contact.email"
                :href="`mailto:${contact.email}`"
                class="flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <Mail class="size-3.5" />
                <span class="break-all">{{ contact.email }}</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
