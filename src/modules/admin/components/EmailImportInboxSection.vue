<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useHandleError } from '@/shared/composables/useHandleError'
import type {
  IEmailImportInboxItem,
  TImportFieldGroup,
  TImportFieldKey,
} from '../types/congregationImport.types'
import { congregationImportApiService } from '../services/congregationImportApiService'

interface FieldState {
  field: TImportFieldKey
  label: string
  group: TImportFieldGroup
  oldValue: string | null
  newValue: string
  apply: boolean
}

interface ItemState {
  messageId: string
  raw: IEmailImportInboxItem
  fields: FieldState[]
  busy: boolean
}

const emit = defineEmits<{ applied: [] }>()

const { t } = useI18n()
const { handleError } = useHandleError()

const loading = ref(false)
const items = ref<ItemState[]>([])

const hasItems = computed(() => items.value.length > 0)

const RESOLUTION_LABELS: Record<string, string> = {
  own_church: 'Własny zbór',
  matched_by_name: 'Dopasowano po nazwie',
  unauthorized: 'Brak uprawnień nadawcy',
  unknown_sender: 'Nieznany nadawca',
  ambiguous: 'Niejednoznaczne',
}

function resolutionLabel(resolution: string): string {
  return t(`admin.emailImportInbox.resolution.${resolution}`, RESOLUTION_LABELS[resolution] ?? resolution)
}

function authBadgeVariant(verdict: string | null): 'success-outline' | 'destructive-outline' | 'outline' {
  if (verdict === 'pass') return 'success-outline'
  if (!verdict) return 'outline'
  return 'destructive-outline'
}

function fieldsByGroup(state: ItemState, group: TImportFieldGroup): FieldState[] {
  return state.fields.filter(field => field.group === group)
}

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString()
}

async function load() {
  loading.value = true
  try {
    const response = await congregationImportApiService.listInbox()
    items.value = response.items.map(item => ({
      messageId: item.message_id,
      raw: item,
      busy: false,
      fields: (item.proposal?.fields ?? []).map(field => ({
        field: field.field,
        label: field.label,
        group: field.group,
        oldValue: field.old_value,
        newValue: field.new_value ?? '',
        apply: field.new_value !== null && field.new_value !== field.old_value,
      })),
    }))
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.emailImportInbox.loadError', 'Nie udało się pobrać kolejki e-maili') })
  } finally {
    loading.value = false
  }
}

async function approve(state: ItemState) {
  state.busy = true
  try {
    await congregationImportApiService.approveInboxItem(state.messageId, {
      fields: state.fields
        .filter(field => field.apply)
        .map(field => ({ field: field.field, value: field.newValue || null, apply: true })),
    })
    toast.success(t('admin.emailImportInbox.approveSuccess', 'Zastosowano zmianę'))
    items.value = items.value.filter(item => item.messageId !== state.messageId)
    emit('applied')
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.emailImportInbox.approveError', 'Nie udało się zastosować zmiany') })
  } finally {
    state.busy = false
  }
}

async function reject(state: ItemState) {
  state.busy = true
  try {
    await congregationImportApiService.rejectInboxItem(state.messageId)
    toast.success(t('admin.emailImportInbox.rejectSuccess', 'Odrzucono wiadomość'))
    items.value = items.value.filter(item => item.messageId !== state.messageId)
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.emailImportInbox.rejectError', 'Nie udało się odrzucić wiadomości') })
  } finally {
    state.busy = false
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ t('admin.emailImportInbox.title', 'Kolejka e-maili od duchownych') }}</CardTitle>
    </CardHeader>
    <CardContent class="space-y-4">
      <p v-if="loading" class="text-sm text-muted-foreground">
        {{ t('admin.emailImportInbox.loading', 'Wczytywanie...') }}
      </p>
      <p v-else-if="!hasItems" class="text-sm text-muted-foreground">
        {{ t('admin.emailImportInbox.empty', 'Brak wiadomości oczekujących na przegląd') }}
      </p>

      <Card v-for="state in items" :key="state.messageId" class="border-dashed">
        <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
          <div class="space-y-1">
            <CardTitle class="text-base">
              {{ state.raw.sender_label ?? state.raw.raw_from }}
            </CardTitle>
            <p class="text-xs text-muted-foreground">
              {{ state.raw.raw_from }} · {{ formatCreatedAt(state.raw.created_at) }}
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">
                {{ resolutionLabel(state.raw.resolution) }}
              </Badge>
              <Badge :variant="authBadgeVariant(state.raw.auth_spf)">
                SPF: {{ state.raw.auth_spf ?? '—' }}
              </Badge>
              <Badge :variant="authBadgeVariant(state.raw.auth_dkim)">
                DKIM: {{ state.raw.auth_dkim ?? '—' }}
              </Badge>
              <Badge :variant="authBadgeVariant(state.raw.auth_dmarc)">
                DMARC: {{ state.raw.auth_dmarc ?? '—' }}
              </Badge>
              <Badge v-if="state.raw.verification_score !== null" variant="outline">
                {{ t('admin.emailImportInbox.trustScore', 'Zaufanie AI') }}: {{ state.raw.verification_score.toFixed(2) }}
              </Badge>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            :disabled="state.busy"
            @click="reject(state)"
          >
            {{ t('admin.emailImportInbox.reject', 'Odrzuć') }}
          </Button>
        </CardHeader>
        <CardContent class="space-y-4">
          <p v-if="state.raw.verification_reasoning" class="text-sm text-muted-foreground">
            {{ state.raw.verification_reasoning }}
          </p>

          <template v-if="state.raw.proposal">
            <p v-if="state.fields.length === 0" class="text-sm text-muted-foreground">
              {{ t('admin.emailImportInbox.noChanges', 'Brak wykrytych zmian pól') }}
            </p>

            <div v-if="fieldsByGroup(state, 'address').length > 0" class="space-y-3">
              <h4 class="text-sm font-semibold">
                {{ t('admin.congregationImport.addressSection', 'Adres') }}
              </h4>
              <div v-for="field in fieldsByGroup(state, 'address')" :key="field.field" class="flex items-center gap-3">
                <Checkbox v-model="field.apply" />
                <div class="flex-1 space-y-1">
                  <Label class="text-xs text-muted-foreground">{{ field.label }}</Label>
                  <div class="flex items-center gap-2 flex-wrap">
                    <span v-if="field.oldValue" class="text-sm text-muted-foreground line-through">
                      {{ field.oldValue }}
                    </span>
                    <Input v-model="field.newValue" class="max-w-xs" />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="fieldsByGroup(state, 'contact').length > 0" class="space-y-3">
              <h4 class="text-sm font-semibold">
                {{ t('admin.congregationImport.contactSection', 'Osoba kontaktowa') }}
              </h4>
              <div v-for="field in fieldsByGroup(state, 'contact')" :key="field.field" class="flex items-center gap-3">
                <Checkbox v-model="field.apply" />
                <div class="flex-1 space-y-1">
                  <Label class="text-xs text-muted-foreground">{{ field.label }}</Label>
                  <div class="flex items-center gap-2 flex-wrap">
                    <span v-if="field.oldValue" class="text-sm text-muted-foreground line-through">
                      {{ field.oldValue }}
                    </span>
                    <Input v-model="field.newValue" class="max-w-xs" />
                  </div>
                </div>
              </div>
            </div>

            <Button :disabled="state.busy" @click="approve(state)">
              {{ state.busy
                ? t('admin.emailImportInbox.applying', 'Zapisywanie...')
                : t('admin.emailImportInbox.approve', 'Zatwierdź i zastosuj') }}
            </Button>
          </template>
          <p v-else class="text-sm text-muted-foreground">
            {{ t('admin.emailImportInbox.noProposal', 'Nie udało się jednoznacznie dopasować zboru — brak zmian do przeglądu. Wklej treść maila w formularzu powyżej, jeśli chcesz zaimportować dane ręcznie.') }}
          </p>
        </CardContent>
      </Card>
    </CardContent>
  </Card>
</template>
