<script setup lang="ts">
import { Mail, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import Card from '@/components/ui/card/Card.vue'
import Checkbox from '@/components/ui/checkbox/Checkbox.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import PersonSuggestionsList from '@/shared/components/PersonSuggestionsList.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import { personSearchService } from '@/shared/services/personSearchService'
import type { IDirectoryFilters, IDirectoryPerson } from '../types/directory.types'
import { directoryApiService } from '../services/directoryApiService'
import type { IPersonSummary } from '@/shared/types/person.type'

const { t } = useI18n()
const { handleError } = useHandleError()

const loading = ref(true)
const accessDenied = ref(false)
const filters = ref<IDirectoryFilters>({ regions: [], serviceTypes: [], groups: [] })

const selectedRegionIds = ref<string[]>([])
const selectedServiceTypeIds = ref<string[]>([])
const selectedGroupIds = ref<string[]>([])

const searching = ref(false)
const results = ref<IDirectoryPerson[]>([])

const addQuery = ref('')
const addSuggestions = ref<IPersonSummary[]>([])
let addDebounce: ReturnType<typeof setTimeout> | null = null

const manualEmail = ref('')

type FilterDimension = 'region' | 'serviceType' | 'group'

function toggle(dimension: FilterDimension, id: string, checked: boolean | 'indeterminate') {
  if (checked === 'indeterminate') return
  const list = dimension === 'region'
    ? selectedRegionIds
    : dimension === 'serviceType'
      ? selectedServiceTypeIds
      : selectedGroupIds
  if (checked) {
    if (!list.value.includes(id)) list.value.push(id)
  } else {
    list.value = list.value.filter(existing => existing !== id)
  }
}

async function loadFilters() {
  loading.value = true
  try {
    filters.value = await directoryApiService.getFilters()
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

async function search() {
  searching.value = true
  try {
    results.value = await directoryApiService.exportPersons({
      regionIds: selectedRegionIds.value,
      serviceTypeIds: selectedServiceTypeIds.value,
      groupIds: selectedGroupIds.value,
    })
  } catch (error) {
    handleError(error)
  } finally {
    searching.value = false
  }
}

function removeResult(id: string) {
  results.value = results.value.filter(p => p.id !== id)
}

function onAddQueryChange(value: string) {
  addQuery.value = value
  if (addDebounce) clearTimeout(addDebounce)
  const trimmed = value.trim()
  if (trimmed.length < 2) {
    addSuggestions.value = []
    return
  }
  addDebounce = setTimeout(async () => {
    try {
      addSuggestions.value = await personSearchService.searchPersons(trimmed)
    } catch {
      addSuggestions.value = []
    }
  }, 300)
}

function addPerson(person: IPersonSummary) {
  if (!person.email) {
    toast.error(t('directory.export.personHasNoEmail', 'Ta osoba nie ma adresu e-mail'))
    return
  }
  if (results.value.some(p => p.id === person.id)) {
    addQuery.value = ''
    addSuggestions.value = []
    return
  }
  results.value.push({
    id: person.id,
    firstName: person.firstName,
    lastName: person.lastName,
    email: person.email,
  })
  addQuery.value = ''
  addSuggestions.value = []
}

function addManualEmail() {
  const email = manualEmail.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    toast.error(t('directory.export.invalidEmail', 'Nieprawidłowy adres e-mail'))
    return
  }
  const id = `manual-${email.toLowerCase()}`
  if (results.value.some(p => p.id === id)) {
    manualEmail.value = ''
    return
  }
  results.value.push({ id, firstName: null, lastName: null, email })
  manualEmail.value = ''
}

function personLabel(person: IDirectoryPerson): string {
  const name = [person.firstName, person.lastName].filter(Boolean).join(' ')
  return name || person.email
}

const plainAddresses = computed<string>(() => results.value.map(p => p.email).join(';'))
const labeledAddresses = computed<string>(() =>
  results.value
    .map((p) => {
      const name = [p.firstName, p.lastName].filter(Boolean).join(' ')
      return name ? `${name} <${p.email}>` : p.email
    })
    .join(', '),
)

async function copyPlain() {
  await navigator.clipboard.writeText(plainAddresses.value)
  toast.success(t('directory.export.copied', 'Skopiowano do schowka'))
}

async function copyLabeled() {
  await navigator.clipboard.writeText(labeledAddresses.value)
  toast.success(t('directory.export.copied', 'Skopiowano do schowka'))
}

onMounted(loadFilters)
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <div>
        <h1 class="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Mail class="size-8 text-primary" />
          {{ t('directory.export.title', 'Eksport adresów e-mail') }}
        </h1>
        <p class="text-muted-foreground mt-2">
          {{ t('directory.export.subtitle', 'Filtruj osoby i skopiuj ich adresy do wklejenia w kliencie poczty') }}
        </p>
      </div>

      <div v-if="loading" class="text-sm text-muted-foreground">
        {{ t('common.loading', 'Ładowanie...') }}
      </div>

      <Card v-else-if="accessDenied" class="p-6">
        <p class="text-sm text-muted-foreground">
          {{ t('directory.export.accessDenied', 'Nie masz roli w organizacji uprawniającej do eksportu adresów.') }}
        </p>
      </Card>

      <div v-else class="space-y-6">
        <Card class="p-4 space-y-4">
          <h3 class="text-lg font-semibold">
            {{ t('directory.export.filters', 'Filtry') }}
          </h3>
          <div class="grid gap-6 sm:grid-cols-3">
            <div class="space-y-2">
              <Label>{{ t('directory.export.region', 'Region') }}</Label>
              <div class="space-y-1">
                <div v-for="region in filters.regions" :key="region.id" class="flex items-center gap-2">
                  <Checkbox
                    :id="`region-${region.id}`"
                    :model-value="selectedRegionIds.includes(region.id)"
                    @update:model-value="toggle('region', region.id, $event)"
                  />
                  <Label :for="`region-${region.id}`" class="text-sm font-normal">{{ region.name }}</Label>
                </div>
                <p v-if="filters.regions.length === 0" class="text-sm text-muted-foreground">
                  {{ t('directory.export.noOptions', 'Brak opcji') }}
                </p>
              </div>
            </div>
            <div class="space-y-2">
              <Label>{{ t('directory.export.role', 'Rola / służba') }}</Label>
              <div class="space-y-1">
                <div v-for="type in filters.serviceTypes" :key="type.id" class="flex items-center gap-2">
                  <Checkbox
                    :id="`service-type-${type.id}`"
                    :model-value="selectedServiceTypeIds.includes(type.id)"
                    @update:model-value="toggle('serviceType', type.id, $event)"
                  />
                  <Label :for="`service-type-${type.id}`" class="text-sm font-normal">{{ type.name }}</Label>
                </div>
                <p v-if="filters.serviceTypes.length === 0" class="text-sm text-muted-foreground">
                  {{ t('directory.export.noOptions', 'Brak opcji') }}
                </p>
              </div>
            </div>
            <div class="space-y-2">
              <Label>{{ t('directory.export.group', 'Grupa') }}</Label>
              <div class="space-y-1">
                <div v-for="group in filters.groups" :key="group.id" class="flex items-center gap-2">
                  <Checkbox
                    :id="`group-${group.id}`"
                    :model-value="selectedGroupIds.includes(group.id)"
                    @update:model-value="toggle('group', group.id, $event)"
                  />
                  <Label :for="`group-${group.id}`" class="text-sm font-normal">{{ group.name }}</Label>
                </div>
                <p v-if="filters.groups.length === 0" class="text-sm text-muted-foreground">
                  {{ t('directory.export.noOptions', 'Brak opcji') }}
                </p>
              </div>
            </div>
          </div>
          <Button type="button" :disabled="searching" @click="search">
            {{ t('directory.export.search', 'Szukaj') }}
          </Button>
        </Card>

        <Card class="p-4 space-y-4">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-lg font-semibold">
              {{ t('directory.export.results', 'Wyniki') }}
            </h3>
            <Badge variant="secondary">
              {{ t('directory.export.resultCount', { count: results.length }) }}
            </Badge>
          </div>

          <ul class="space-y-2">
            <li
              v-for="person in results"
              :key="person.id"
              class="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
            >
              <div>
                <p class="font-medium">
                  {{ personLabel(person) }}
                </p>
                <p class="text-sm text-muted-foreground">
                  {{ person.email }}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                @click="removeResult(person.id)"
              >
                <Trash2 class="size-4" />
              </Button>
            </li>
            <li v-if="results.length === 0" class="text-sm text-muted-foreground">
              {{ t('directory.export.empty', 'Brak wyników — zastosuj filtry lub dodaj ręcznie') }}
            </li>
          </ul>

          <div class="grid gap-3 sm:grid-cols-2 border-t pt-4">
            <div class="relative space-y-1">
              <Label>{{ t('directory.export.addPerson', 'Dodaj osobę') }}</Label>
              <Input
                :model-value="addQuery"
                @update:model-value="onAddQueryChange(String($event))"
                @blur="addSuggestions = []"
              />
              <PersonSuggestionsList :suggestions="addSuggestions" @select="addPerson" />
            </div>
            <div class="space-y-1">
              <Label>{{ t('directory.export.addEmail', 'Dodaj dowolny e-mail') }}</Label>
              <div class="flex gap-2">
                <Input v-model="manualEmail" type="email" @keyup.enter="addManualEmail" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  @click="addManualEmail"
                >
                  <Plus class="size-4" />
                </Button>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-2 border-t pt-4">
            <Button
              type="button"
              variant="outline"
              :disabled="results.length === 0"
              @click="copyPlain"
            >
              {{ t('directory.export.copyPlain', 'Kopiuj same adresy') }}
            </Button>
            <Button
              type="button"
              variant="outline"
              :disabled="results.length === 0"
              @click="copyLabeled"
            >
              {{ t('directory.export.copyLabeled', 'Kopiuj z etykietami') }}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
