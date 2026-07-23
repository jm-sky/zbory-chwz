<script setup lang="ts">
import { Pencil, Search } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import PersonSuggestionsList from '@/shared/components/PersonSuggestionsList.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import { personSearchService } from '@/shared/services/personSearchService'
import { formatPhoneNumber } from '@/shared/utils/formatPhone'
import type { IPersonBrowse } from '../types/directory.types'
import { directoryApiService } from '../services/directoryApiService'
import PersonChangeHistorySection from './PersonChangeHistorySection.vue'
import type { IPersonSummary } from '@/shared/types/person.type'

const { t } = useI18n()
const { handleError } = useHandleError()

const query = ref('')
const loading = ref(true)
const accessDenied = ref(false)
const persons = ref<IPersonBrowse[]>([])
let searchDebounce: ReturnType<typeof setTimeout> | null = null

const editDialogOpen = ref(false)
const editingPerson = ref<IPersonBrowse | null>(null)
const editForm = ref({ firstName: '', lastName: '', email: '', phone: '' })
const saving = ref(false)

const mergeQuery = ref('')
const mergeSuggestions = ref<IPersonSummary[]>([])
const mergeCandidate = ref<IPersonSummary | null>(null)
const merging = ref(false)
let mergeDebounce: ReturnType<typeof setTimeout> | null = null

function personLabel(person: IPersonBrowse | IPersonSummary): string {
  const name = [person.firstName, person.lastName].filter(Boolean).join(' ')
  return name || person.email || person.phone || '—'
}

async function load() {
  loading.value = true
  try {
    persons.value = await directoryApiService.listPersons(query.value || undefined)
  } catch (error) {
    const status = (error as { response?: { status?: number } }).response?.status
    if (status === 403) {
      accessDenied.value = true
    } else {
      handleError(error)
    }
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(load, 300)
}

function openEdit(person: IPersonBrowse) {
  editingPerson.value = person
  editForm.value = {
    firstName: person.firstName ?? '',
    lastName: person.lastName ?? '',
    email: person.email ?? '',
    phone: person.phone ?? '',
  }
  mergeQuery.value = ''
  mergeSuggestions.value = []
  mergeCandidate.value = null
  editDialogOpen.value = true
}

async function saveEdit() {
  if (!editingPerson.value) return
  saving.value = true
  try {
    const updated = await directoryApiService.updatePerson(editingPerson.value.id, {
      firstName: editForm.value.firstName || undefined,
      lastName: editForm.value.lastName || undefined,
      email: editForm.value.email || undefined,
      phone: editForm.value.phone || undefined,
    })
    const index = persons.value.findIndex(p => p.id === updated.id)
    if (index >= 0) persons.value[index] = { ...persons.value[index], ...updated }
    editingPerson.value = updated
    toast.success(t('directory.persons.updated', 'Zapisano zmiany'))
  } catch (error) {
    handleError(error)
  } finally {
    saving.value = false
  }
}

function onMergeQueryChange(value: string) {
  mergeQuery.value = value
  mergeCandidate.value = null
  if (mergeDebounce) clearTimeout(mergeDebounce)
  const trimmed = value.trim()
  if (trimmed.length < 2) {
    mergeSuggestions.value = []
    return
  }
  mergeDebounce = setTimeout(async () => {
    try {
      const results = await personSearchService.searchPersons(trimmed)
      mergeSuggestions.value = results.filter(p => p.id !== editingPerson.value?.id)
    } catch {
      mergeSuggestions.value = []
    }
  }, 300)
}

function selectMergeCandidate(person: IPersonSummary) {
  mergeCandidate.value = person
  mergeQuery.value = personLabel(person)
  mergeSuggestions.value = []
}

async function confirmMerge() {
  if (!editingPerson.value || !mergeCandidate.value) return
  const confirmed = confirm(
    t('directory.persons.mergeConfirm', {
      duplicate: personLabel(mergeCandidate.value),
      keep: personLabel(editingPerson.value),
    }),
  )
  if (!confirmed) return

  merging.value = true
  try {
    const merged = await directoryApiService.mergePersons({
      keepPersonId: editingPerson.value.id,
      mergePersonId: mergeCandidate.value.id,
    })
    editingPerson.value = merged
    editForm.value = {
      firstName: merged.firstName ?? '',
      lastName: merged.lastName ?? '',
      email: merged.email ?? '',
      phone: merged.phone ?? '',
    }
    mergeQuery.value = ''
    mergeCandidate.value = null
    toast.success(t('directory.persons.merged', 'Osoby scalone'))
    await load()
  } catch (error) {
    handleError(error)
  } finally {
    merging.value = false
  }
}

function affiliationLabel(affiliation: IPersonBrowse['affiliations'][number]): string {
  if (affiliation.kind === 'group') {
    return t('directory.persons.groupBadge', { name: affiliation.label })
  }
  return affiliation.context ? `${affiliation.label} · ${affiliation.context}` : affiliation.label
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div v-if="!accessDenied" class="relative">
      <Search class="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
      <Input
        v-model="query"
        class="pl-8"
        :placeholder="t('directory.persons.searchPlaceholder', 'Szukaj po imieniu, nazwisku, e-mailu, telefonie...')"
        @update:model-value="onSearchInput"
      />
    </div>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>

    <p v-else-if="accessDenied" class="text-sm text-muted-foreground">
      {{ t('directory.persons.accessDenied', 'Nie masz roli w organizacji uprawniającej do przeglądarki osób.') }}
    </p>

    <ul v-else class="space-y-2">
      <li
        v-for="person in persons"
        :key="person.id"
        class="flex items-start justify-between gap-2 rounded-md border px-3 py-2 cursor-pointer hover:border-primary"
        @click="openEdit(person)"
      >
        <div class="min-w-0 space-y-1">
          <p class="font-medium">
            {{ personLabel(person) }}
          </p>
          <p class="text-sm text-muted-foreground">
            {{ [person.email, formatPhoneNumber(person.phone)].filter(Boolean).join(' · ') || '—' }}
          </p>
          <div v-if="person.affiliations.length > 0" class="flex flex-wrap gap-1">
            <Badge v-for="(affiliation, i) in person.affiliations" :key="i" variant="secondary">
              {{ affiliationLabel(affiliation) }}
            </Badge>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          @click.stop="openEdit(person)"
        >
          <Pencil class="size-4" />
        </Button>
      </li>
      <li v-if="persons.length === 0" class="text-sm text-muted-foreground">
        {{ t('directory.persons.empty', 'Brak osób') }}
      </li>
    </ul>

    <Dialog v-model:open="editDialogOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ t('directory.persons.editTitle', 'Edytuj osobę') }}</DialogTitle>
        </DialogHeader>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="space-y-1">
            <Label>{{ t('directory.persons.firstName', 'Imię') }}</Label>
            <Input v-model="editForm.firstName" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('directory.persons.lastName', 'Nazwisko') }}</Label>
            <Input v-model="editForm.lastName" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('directory.persons.email', 'E-mail') }}</Label>
            <Input v-model="editForm.email" type="email" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('directory.persons.phone', 'Telefon') }}</Label>
            <Input v-model="editForm.phone" />
          </div>
        </div>

        <div v-if="editingPerson && editingPerson.affiliations.length > 0" class="flex flex-wrap gap-1">
          <Badge v-for="(affiliation, i) in editingPerson.affiliations" :key="i" variant="secondary">
            {{ affiliationLabel(affiliation) }}
          </Badge>
        </div>

        <DialogFooter>
          <Button type="button" :disabled="saving" @click="saveEdit">
            {{ t('common.save', 'Zapisz') }}
          </Button>
        </DialogFooter>

        <div class="relative space-y-2 border-t pt-4">
          <Label>{{ t('directory.persons.mergeLabel', 'Scal z inną osobą (duplikat)') }}</Label>
          <Input
            :model-value="mergeQuery"
            @update:model-value="onMergeQueryChange(String($event))"
            @blur="mergeSuggestions = []"
          />
          <PersonSuggestionsList :suggestions="mergeSuggestions" @select="selectMergeCandidate" />
          <Button
            type="button"
            variant="destructive"
            :disabled="!mergeCandidate || merging"
            @click="confirmMerge"
          >
            {{ t('directory.persons.mergeButton', 'Scal') }}
          </Button>
        </div>

        <PersonChangeHistorySection
          v-if="editingPerson"
          :key="editingPerson.id"
          :person-id="editingPerson.id"
          class="border-t pt-4"
        />
      </DialogContent>
    </Dialog>
  </div>
</template>
