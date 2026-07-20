<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { FileText, Sparkles } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { congregationKeys } from '@/modules/congregations/utils/congregationKeys'
import { useHandleError } from '@/shared/composables/useHandleError'
import type {
  IImportApplyItem,
  IImportCandidateTenant,
  TImportFieldGroup,
  TImportFieldKey,
} from '../types/congregationImport.types'
import EmailImportInboxSection from '../components/EmailImportInboxSection.vue'
import ImportFieldDiffGroup from '../components/ImportFieldDiffGroup.vue'
import { AdminRouteNames } from '../routes'
import { congregationImportApiService } from '../services/congregationImportApiService'

const CREATE_NEW_VALUE = '__create_new__'

interface FieldState {
  field: TImportFieldKey
  label: string
  group: TImportFieldGroup
  oldValue: string | null
  newValue: string
  apply: boolean
}

interface ProposalState {
  proposalId: string
  detectedName: string
  matchType: 'matched' | 'new'
  confidence: number
  contactContext: string | null
  contactPersonId: string | null
  skip: boolean
  targetTenantId: string
  congregationName: string
  fields: FieldState[]
}

const { t } = useI18n()
const router = useRouter()
const { handleError } = useHandleError()
const queryClient = useQueryClient()

const rawText = ref('')
const analyzing = ref(false)
const applying = ref(false)
const candidates = ref<IImportCandidateTenant[]>([])
const proposalStates = ref<ProposalState[]>([])

const hasProposals = computed(() => proposalStates.value.length > 0)

function matchLabel(state: ProposalState): string {
  if (state.matchType === 'matched') {
    return `${t('admin.congregationImport.matched', 'Dopasowano')} (${state.confidence}%)`
  }
  return t('admin.congregationImport.new', 'Nowy zbór')
}

async function analyze() {
  if (!rawText.value.trim()) return

  analyzing.value = true
  try {
    const response = await congregationImportApiService.analyze(rawText.value)
    candidates.value = response.candidates
    proposalStates.value = response.proposals.map(proposal => ({
      proposalId: proposal.proposal_id,
      detectedName: proposal.detected_name,
      matchType: proposal.match_type,
      confidence: proposal.confidence,
      contactContext: proposal.contact_context,
      contactPersonId: proposal.contact_person_id,
      skip: false,
      targetTenantId: proposal.tenant_id ?? CREATE_NEW_VALUE,
      congregationName: proposal.detected_name,
      fields: proposal.fields.map(field => ({
        field: field.field,
        label: field.label,
        group: field.group,
        oldValue: field.old_value,
        newValue: field.new_value ?? '',
        apply: field.new_value !== null && field.new_value !== field.old_value,
      })),
    }))
    if (proposalStates.value.length === 0) {
      toast.info(t('admin.congregationImport.noneFound', 'Nie znaleziono żadnego zboru w tekście'))
    }
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.congregationImport.analyzeError', 'Nie udało się przeanalizować tekstu') })
  } finally {
    analyzing.value = false
  }
}

function buildApplyItems(): IImportApplyItem[] {
  return proposalStates.value.map((state) => {
    if (state.skip) {
      return { action: 'skip', fields: [] }
    }

    const fields = state.fields
      .filter(field => field.apply)
      .map(field => ({ field: field.field, value: field.newValue || null, apply: true }))

    if (state.targetTenantId === CREATE_NEW_VALUE) {
      return { action: 'create', congregation_name: state.congregationName, fields }
    }

    return { action: 'update', tenant_id: state.targetTenantId, contact_person_id: state.contactPersonId, fields }
  })
}

async function apply() {
  applying.value = true
  try {
    const result = await congregationImportApiService.apply({ items: buildApplyItems() })
    toast.success(
      `${t('admin.congregationImport.applySuccess', 'Zastosowano zmiany')}: `
      + `${t('admin.congregationImport.created', 'utworzono')} ${result.created}, `
      + `${t('admin.congregationImport.updated', 'zaktualizowano')} ${result.updated}, `
      + `${t('admin.congregationImport.skipped', 'pominięto')} ${result.skipped}`,
    )
    await queryClient.invalidateQueries({ queryKey: congregationKeys.all, refetchType: 'all' })
    rawText.value = ''
    proposalStates.value = []
    candidates.value = []
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.congregationImport.applyError', 'Nie udało się zapisać zmian') })
  } finally {
    applying.value = false
  }
}

function goBack() {
  router.push({ name: AdminRouteNames.congregations })
}

async function onInboxItemApplied() {
  await queryClient.invalidateQueries({ queryKey: congregationKeys.all, refetchType: 'all' })
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="Sparkles"
        :label="t('admin.congregationImport.title', 'Import adresów z tekstu')"
        :description="t('admin.congregationImport.subtitle', 'Wklej notatkę z adresami zborów, przejrzyj zmiany i zatwierdź')"
        with-back-button
        @back="goBack"
      />

      <EmailImportInboxSection @applied="onInboxItemApplied" />

      <Card>
        <CardHeader>
          <CardTitle>{{ t('admin.congregationImport.pasteTitle', 'Wklej tekst') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <Textarea
            v-model="rawText"
            :placeholder="t('admin.congregationImport.placeholder', 'Wklej notatkę z adresami zborów...')"
            rows="8"
          />
          <Button :disabled="!rawText.trim() || analyzing" @click="analyze">
            <FileText class="size-4" />
            {{ analyzing
              ? t('admin.congregationImport.analyzing', 'Analizowanie...')
              : t('admin.congregationImport.analyze', 'Analizuj') }}
          </Button>
        </CardContent>
      </Card>

      <div v-if="hasProposals" class="space-y-4">
        <Card v-for="state in proposalStates" :key="state.proposalId">
          <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
            <div class="space-y-1">
              <CardTitle>{{ state.detectedName }}</CardTitle>
              <Badge :variant="state.matchType === 'matched' ? 'success-outline' : 'primary-outline'">
                {{ matchLabel(state) }}
              </Badge>
            </div>
            <label class="flex items-center gap-2 text-sm shrink-0">
              <Checkbox v-model="state.skip" />
              {{ t('admin.congregationImport.skip', 'Pomiń') }}
            </label>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="space-y-2">
                <Label>{{ t('admin.congregationImport.target', 'Dopasowanie do zboru') }}</Label>
                <Select v-model="state.targetTenantId">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="CREATE_NEW_VALUE">
                      {{ t('admin.congregationImport.createNew', 'Utwórz nowy zbór') }}
                    </SelectItem>
                    <SelectItem
                      v-for="candidate in candidates"
                      :key="candidate.tenant_id"
                      :value="candidate.tenant_id"
                    >
                      {{ candidate.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div v-if="state.targetTenantId === CREATE_NEW_VALUE" class="space-y-2">
                <Label>{{ t('admin.congregationImport.name', 'Nazwa nowego zboru') }}</Label>
                <Input v-model="state.congregationName" />
              </div>
            </div>

            <p v-if="state.fields.length === 0" class="text-sm text-muted-foreground">
              {{ t('admin.congregationImport.noChanges', 'Brak zmian do zastosowania') }}
            </p>

            <ImportFieldDiffGroup :fields="state.fields" group="address">
              {{ t('admin.congregationImport.addressSection', 'Adres') }}
            </ImportFieldDiffGroup>

            <ImportFieldDiffGroup :fields="state.fields" group="contact">
              {{ t('admin.congregationImport.contactSection', 'Osoba kontaktowa') }}
              <span v-if="state.contactContext" class="font-normal text-muted-foreground">
                ({{ state.contactContext }})
              </span>
            </ImportFieldDiffGroup>
          </CardContent>
        </Card>

        <Button :disabled="applying" @click="apply">
          {{ applying
            ? t('admin.congregationImport.applying', 'Zapisywanie...')
            : t('admin.congregationImport.apply', 'Zastosuj zaznaczone zmiany') }}
        </Button>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
