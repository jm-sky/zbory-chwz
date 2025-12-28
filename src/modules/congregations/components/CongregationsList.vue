<script setup lang="ts">
import { Church, Clock, Mail, MapPin, Phone, User } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import { useCongregations } from '../composables/useCongregations'

const { t } = useI18n()
const { data: congregations, isLoading, error } = useCongregations()

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
</script>

<template>
  <div class="space-y-4">
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

    <!-- Congregations List -->
    <div v-else class="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
      <div
        v-for="congregation in congregations"
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

          <!-- Contact Person -->
          <div v-if="congregation.contact_name" class="flex items-start gap-2 text-sm">
            <User class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div class="flex-1 min-w-0">
              <span class="font-medium text-foreground">{{ congregation.contact_name }}</span>
              <span v-if="congregation.contact_title" class="text-muted-foreground">
                {{ ` - ${congregation.contact_title}` }}
              </span>
            </div>
          </div>

          <!-- Contact Info -->
          <div v-if="congregation.contact_phone || congregation.contact_email" class="ml-6 space-y-1.5 text-sm">
            <a
              v-if="congregation.contact_phone"
              :href="`tel:${congregation.contact_phone}`"
              class="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <Phone class="size-3.5" />
              <span>{{ congregation.contact_phone }}</span>
            </a>
            <a
              v-if="congregation.contact_email"
              :href="`mailto:${congregation.contact_email}`"
              class="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <Mail class="size-3.5" />
              <span class="break-all">{{ congregation.contact_email }}</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
