<script setup lang="ts">
import { Church, Clock, Edit, EyeOff, Mail, MapPin, MoreHorizontal, Phone, Trash2, User } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatPhoneNumber } from '@/shared/utils/formatPhone'
import type { ICongregationDetailed } from '../types/congregation.types'
import { calculateCongregationCompleteness } from '../utils/congregationCompleteness'
import { formatAddress, formatServiceTimes } from '../utils/congregationDisplay'
import { contactsOf } from '../utils/exportCongregations'
import CongregationCompletenessIndicator from './CongregationCompletenessIndicator.vue'

const { t } = useI18n()

const { congregation, canManage, canDelete, showCompleteness = false } = defineProps<{
  congregation: ICongregationDetailed
  canManage: boolean
  canDelete: boolean
  showCompleteness?: boolean
}>()

const emit = defineEmits<{
  open: []
  edit: []
  unpublish: []
  delete: []
}>()

const completeness = computed(() => {
  const contacts = contactsOf(congregation)
  return calculateCongregationCompleteness({
    description: congregation.description,
    street: congregation.street,
    postal_code: congregation.postal_code,
    province: congregation.province,
    website: congregation.website,
    latitude: congregation.latitude,
    longitude: congregation.longitude,
    service_times_count: congregation.service_times?.length,
    card_contacts_count: congregation.card_contacts?.length,
    has_contact_email: contacts.some(c => !!c.email),
    has_contact_phone: contacts.some(c => !!c.phone),
  })
})
</script>

<template>
  <div
    :class="[
      'group rounded-lg border p-6 transition-all hover:shadow-lg',
      congregation.type !== 'branch' ? 'cursor-pointer' : '',
      congregation.status === 'draft'
        ? 'border-dashed bg-muted/20 border-muted-foreground/30 opacity-75 hover:border-muted-foreground/50'
        : congregation.status === 'published_unverified'
          ? 'bg-muted/30 border-muted-foreground/20 hover:border-muted-foreground/40 opacity-90'
          : 'bg-card hover:border-primary/50 hover:-translate-y-0.5 transition-all duration-200 ease-in-out delay-100'
    ]"
    @click="emit('open')"
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
              congregation.status === 'draft' || congregation.status === 'published_unverified'
                ? 'text-muted-foreground'
                : 'text-foreground'
            ]"
          >
            {{ congregation.name }}
          </h3>
          <Badge v-if="congregation.type === 'branch'" variant="secondary">
            {{ t('congregations.list.branch') }}
          </Badge>
          <Badge
            v-if="congregation.status === 'draft'"
            variant="outline"
            class="border-dashed text-muted-foreground border-muted-foreground/50"
          >
            {{ t('congregations.status.draft', 'Szkic') }}
          </Badge>
          <Badge
            v-else-if="congregation.status === 'published_unverified'"
            variant="outline"
            class="opacity-60 text-muted-foreground border-muted-foreground/50"
          >
            {{ t('congregations.status.unverified', 'Draft') }}
          </Badge>
          <CongregationCompletenessIndicator
            v-if="showCompleteness && congregation.type !== 'branch'"
            compact
            :score="completeness.score"
            :missing-fields="completeness.missingFields"
            @click.stop
          />
        </div>
        <p
          v-if="congregation.type === 'branch' && congregation.parent_name"
          class="mt-1 text-sm text-muted-foreground"
        >
          {{ t('congregations.list.branchOf', { name: congregation.parent_name }) }}
        </p>
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
      <DropdownMenu v-if="canManage">
        <DropdownMenuTrigger as-child>
          <Button
            variant="ghost"
            size="icon"
            class="shrink-0"
            @click.stop
          >
            <MoreHorizontal class="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" @click.stop>
          <DropdownMenuItem @click="emit('edit')">
            <Edit class="size-4" />
            <span>{{ t('common.edit', 'Edytuj') }}</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            v-if="congregation.status === 'published' || congregation.status === 'published_unverified'"
            @click="emit('unpublish')"
          >
            <EyeOff class="size-4" />
            <span>{{ t('congregations.list.unpublish', 'Cofnij publikację') }}</span>
          </DropdownMenuItem>
          <template v-if="canDelete">
            <DropdownMenuSeparator />
            <DropdownMenuItem
              class="text-destructive focus:text-destructive"
              @click="emit('delete')"
            >
              <Trash2 class="size-4" />
              <span>{{ t('common.delete', 'Usuń') }}</span>
            </DropdownMenuItem>
          </template>
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
        v-for="(contact, contactIndex) in contactsOf(congregation)"
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
            @click.stop
          >
            <Phone class="size-3.5" />
            <span>{{ formatPhoneNumber(contact.phone) }}</span>
          </a>
          <a
            v-if="contact.email"
            :href="`mailto:${contact.email}`"
            class="flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
            @click.stop
          >
            <Mail class="size-3.5" />
            <span class="break-all">{{ contact.email }}</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>
