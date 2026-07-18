<script setup lang="ts">
import { Church, Edit, EyeOff, MoreHorizontal, Trash2 } from 'lucide-vue-next'
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

const contacts = computed(() => contactsOf(congregation))
const firstContact = computed(() => contacts.value[0])
const completeness = computed(() =>
  calculateCongregationCompleteness({
    description: congregation.description,
    street: congregation.street,
    postal_code: congregation.postal_code,
    province: congregation.province,
    website: congregation.website,
    latitude: congregation.latitude,
    longitude: congregation.longitude,
    service_times_count: congregation.service_times?.length,
    card_contacts_count: congregation.card_contacts?.length,
    has_contact_email: contacts.value.some(c => !!c.email),
    has_contact_phone: contacts.value.some(c => !!c.phone),
  }),
)
</script>

<template>
  <div
    :class="[
      'group flex items-start gap-3 p-4 transition-colors hover:bg-muted/50 sm:items-center',
      congregation.type !== 'branch' ? 'cursor-pointer' : '',
      congregation.status === 'draft'
        ? 'bg-muted/20 opacity-75'
        : congregation.status === 'published_unverified'
          ? 'bg-muted/30 opacity-90'
          : ''
    ]"
    @click="emit('open')"
  >
    <div class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
      <Church class="size-4 text-primary" />
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2 flex-wrap">
        <h3
          :class="[
            'truncate font-medium leading-tight',
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
      <p v-if="formatAddress(congregation)" class="line-clamp-1 text-sm text-muted-foreground">
        {{ formatAddress(congregation) }}
      </p>
      <p v-if="formatServiceTimes(congregation.service_times)" class="line-clamp-1 text-sm text-muted-foreground">
        {{ formatServiceTimes(congregation.service_times) }}
      </p>
      <p v-if="firstContact" class="line-clamp-1 text-sm text-muted-foreground">
        {{ firstContact.name }}
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
</template>
