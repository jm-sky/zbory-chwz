<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { churchApiService } from '@/modules/congregations/services/churchApiService'
import { useHandleError } from '@/shared/composables/useHandleError'
import { personSearchService } from '@/shared/services/personSearchService'
import { formatPhoneNumber } from '@/shared/utils/formatPhone'
import type { GovernanceScopeType } from '../types/governance.types'
import { governanceApiService } from '../services/governanceApiService'
import type { IGrantableRole } from '@/modules/congregations/types/church.types'
import type { IPersonSummary } from '@/shared/types/person.type'

const { scopeType, scopeId } = defineProps<{
  scopeType: GovernanceScopeType
  scopeId: string
}>()

const open = defineModel<boolean>('open', { required: true })

const emit = defineEmits<{
  granted: []
}>()

const { t } = useI18n()
const { handleError } = useHandleError()

const query = ref('')
const suggestions = ref<IPersonSummary[]>([])
const selectedPerson = ref<IPersonSummary | null>(null)
const grantableRoles = ref<IGrantableRole[]>([])
const selectedRole = ref('')
const searching = ref(false)
const submitting = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function personLabel(person: IPersonSummary): string {
  const name = [person.firstName, person.lastName].filter(Boolean).join(' ')
  return name || person.email || formatPhoneNumber(person.phone) || '—'
}

function personDetail(person: IPersonSummary): string {
  return [person.email, formatPhoneNumber(person.phone)].filter(Boolean).join(' · ')
}

function onQueryChange(value: string) {
  query.value = value
  selectedPerson.value = null
  if (debounceTimer) clearTimeout(debounceTimer)

  const trimmed = value.trim()
  if (trimmed.length < 2) {
    suggestions.value = []
    return
  }

  debounceTimer = setTimeout(async () => {
    searching.value = true
    try {
      suggestions.value = await personSearchService.searchPersons(trimmed)
    } catch (error) {
      handleError(error)
    } finally {
      searching.value = false
    }
  }, 300)
}

function selectPerson(person: IPersonSummary) {
  selectedPerson.value = person
  query.value = personLabel(person)
  suggestions.value = []
}

const canSubmit = computed<boolean>(() =>
  !!selectedPerson.value && !!selectedPerson.value.userId && !!selectedRole.value && !submitting.value,
)

async function loadGrantableRoles() {
  try {
    grantableRoles.value = await churchApiService.listGrantableRoles(scopeType, scopeId)
  } catch (error) {
    handleError(error)
  }
}

function resetForm() {
  query.value = ''
  suggestions.value = []
  selectedPerson.value = null
  selectedRole.value = ''
}

watch(open, (isOpen) => {
  if (isOpen) {
    resetForm()
    void loadGrantableRoles()
  }
})

async function submit() {
  if (!selectedPerson.value?.userId || !selectedRole.value) return

  submitting.value = true
  try {
    await governanceApiService.createRoleAssignment({
      userId: selectedPerson.value.userId,
      roleName: selectedRole.value,
      scopeType,
      scopeId,
    })
    toast.success(t('governance.roles.grantSuccess', 'Rola nadana'))
    open.value = false
    emit('granted')
  } catch (error) {
    handleError(error, { fallbackMessage: t('governance.roles.grantError', 'Nie udało się nadać roli') })
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-lg">
      <DialogHeader>
        <DialogTitle>{{ t('governance.roles.addTitle', 'Nadaj rolę') }}</DialogTitle>
        <DialogDescription>
          {{ t('governance.roles.addDescription', 'Znajdź osobę z istniejącym kontem i wybierz rolę do nadania w tym zasięgu.') }}
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4">
        <div class="relative space-y-1">
          <Label>{{ t('governance.roles.personSearchLabel', 'Osoba') }}</Label>
          <Input
            :model-value="query"
            :placeholder="t('governance.roles.personSearchPlaceholder', 'Szukaj po imieniu, nazwisku, emailu lub telefonie')"
            @update:model-value="onQueryChange(String($event))"
          />
          <ul
            v-if="suggestions.length > 0"
            class="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border bg-popover shadow-md"
          >
            <li v-for="person in suggestions" :key="person.id">
              <button
                type="button"
                class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-sm hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!person.userId"
                @mousedown.prevent="selectPerson(person)"
              >
                <span class="font-medium">{{ personLabel(person) }}</span>
                <span class="text-xs text-muted-foreground">
                  {{ personDetail(person) }}
                  <template v-if="!person.userId">
                    · {{ t('governance.roles.personNoAccount', 'Brak konta — nie można nadać roli') }}
                  </template>
                </span>
              </button>
            </li>
          </ul>
          <p v-if="selectedPerson && !selectedPerson.userId" class="text-xs text-destructive">
            {{ t('governance.roles.personNoAccount', 'Brak konta — nie można nadać roli') }}
          </p>
        </div>

        <div class="space-y-1">
          <Label>{{ t('governance.roles.roleLabel', 'Rola') }}</Label>
          <Select v-model="selectedRole">
            <SelectTrigger class="w-full">
              <SelectValue :placeholder="t('governance.roles.rolePlaceholder', 'Wybierz rolę')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="role in grantableRoles" :key="role.name" :value="role.name">
                {{ t(`congregations.people.roles.${role.name}`, role.name) }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p v-if="grantableRoles.length === 0" class="text-xs text-muted-foreground">
            {{ t('governance.roles.noGrantableRoles', 'Nie możesz nadać żadnej roli w tym zasięgu') }}
          </p>
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" @click="open = false">
          {{ t('common.cancel', 'Anuluj') }}
        </Button>
        <Button
          type="button"
          :disabled="!canSubmit"
          :loading="submitting"
          @click="submit"
        >
          {{ t('governance.roles.add', 'Nadaj rolę') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
