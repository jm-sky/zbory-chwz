<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Contact, Link2, Mail, Phone, RefreshCw, Sparkles, Unlink } from 'lucide-vue-next'
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
import SearchInput from '@/components/ui/input/SearchInput.vue'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type {
  IGoogleContactChurchApplyItem,
  IGoogleContactPersonApplyItem,
  IGoogleContactSuggestion,
  TGoogleContactMatchType,
  TGoogleContactType,
} from '../types/googleContacts.types'
import { AdminRouteNames } from '../routes'
import { googleContactsApiService } from '../services/googleContactsApiService'

const CREATE_NEW_VALUE = '__create_new__'
const GOOGLE_CONTACTS_OAUTH_STATE_KEY = 'google_contacts_oauth_state'
const DEFAULT_KEYWORDS = 'zbór, chwz'

interface SelectableContact {
  contact: IGoogleContactSuggestion
  selected: boolean
  type: TGoogleContactType
}

type TMatchLocation = 'name' | 'description'

interface ChurchProposalState {
  resourceName: string
  matchType: TGoogleContactMatchType
  confidence: number
  matchedName: string | null
  skip: boolean
  targetTenantId: string
  name: string
  street: string
  city: string
  postalCode: string
  province: string
  country: string
  phone: string
  email: string
}

interface PersonProposalState {
  resourceName: string
  matchType: TGoogleContactMatchType
  personId: string | null
  matchedName: string | null
  matchedBy: 'email' | 'phone' | null
  forceCreateNew: boolean
  skip: boolean
  firstName: string
  lastName: string
  email: string
  phone: string
  assignToChurch: boolean
  churchId: string
  serviceTypeId: string
  customServiceName: string
}

const { t } = useI18n()
const router = useRouter()
const { handleError } = useHandleError()
const queryClient = useQueryClient()

const connectionQueryKey = ['google-contacts', 'connection']

const { data: connection, isLoading: isConnectionLoading } = useQuery({
  queryKey: connectionQueryKey,
  queryFn: () => googleContactsApiService.getConnection(),
  staleTime: 60 * 1000,
})

const isConnecting = ref(false)
const totalFetched = ref<number | null>(null)
const isLoadingContacts = ref(false)
const hasLoadedContacts = computed(() => totalFetched.value !== null)
const selectableContacts = ref<SelectableContact[]>([])
const selectedCount = computed(() => selectableContacts.value.filter(c => c.selected).length)

const keywordsInput = ref<string>(DEFAULT_KEYWORDS)
const keywordsList = computed<string[]>(() =>
  keywordsInput.value.split(',').map(keyword => keyword.trim()).filter(Boolean),
)
const keywordsUsed = ref<string[]>([])

const searchQuery = ref<string>('')
const matchInName = ref<boolean>(true)
const matchInDescription = ref<boolean>(true)

function matchLocations(contact: IGoogleContactSuggestion, keywords: string[]): TMatchLocation[] {
  const nameText = `${contact.displayName ?? ''} ${contact.organizationName ?? ''}`.toLowerCase()
  const descriptionText = (contact.notes ?? '').toLowerCase()
  const lowerKeywords = keywords.map(keyword => keyword.toLowerCase())
  const locations: TMatchLocation[] = []
  if (lowerKeywords.some(keyword => nameText.includes(keyword))) locations.push('name')
  if (lowerKeywords.some(keyword => descriptionText.includes(keyword))) locations.push('description')
  return locations
}

const filteredContacts = computed<SelectableContact[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return selectableContacts.value.filter((item) => {
    if (query) {
      const haystack = [item.contact.displayName, item.contact.organizationName, item.contact.notes]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(query)) return false
    }
    const locations = matchLocations(item.contact, keywordsUsed.value)
    return (matchInName.value && locations.includes('name')) || (matchInDescription.value && locations.includes('description'))
  })
})

const visibleSelectionState = computed<boolean | 'indeterminate'>(() => {
  const visible = filteredContacts.value
  if (visible.length === 0) return false
  const selectedVisible = visible.filter(item => item.selected).length
  if (selectedVisible === 0) return false
  return selectedVisible === visible.length ? true : 'indeterminate'
})

function toggleVisibleSelection(value: boolean | 'indeterminate') {
  const shouldSelect = value === true
  for (const item of filteredContacts.value) item.selected = shouldSelect
}

const isAnalyzing = ref(false)
const isApplying = ref(false)
const churchProposals = ref<ChurchProposalState[]>([])
const personProposals = ref<PersonProposalState[]>([])
const candidateTenants = ref<{ tenantId: string, name: string }[]>([])
const serviceTypes = ref<{ id: string, name: string }[]>([])
const hasProposals = computed(() => churchProposals.value.length > 0 || personProposals.value.length > 0)

async function connect() {
  isConnecting.value = true
  try {
    const { authUrl, state } = await googleContactsApiService.getAuthUrl()
    sessionStorage.setItem(GOOGLE_CONTACTS_OAUTH_STATE_KEY, state)
    window.location.href = authUrl
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.connectError', 'Nie udało się rozpocząć łączenia z Google') })
    isConnecting.value = false
  }
}

function resetLoadedState() {
  selectableContacts.value = []
  totalFetched.value = null
  churchProposals.value = []
  personProposals.value = []
  keywordsUsed.value = []
  searchQuery.value = ''
  matchInName.value = true
  matchInDescription.value = true
}

const disconnectMutation = useMutation({
  mutationFn: () => googleContactsApiService.disconnect(),
  onSuccess: async () => {
    toast.success(t('admin.googleContacts.disconnectSuccess', 'Odłączono Google Contacts'))
    resetLoadedState()
    await queryClient.invalidateQueries({ queryKey: connectionQueryKey })
  },
  onError: (error: unknown) => handleError(error, { fallbackMessage: t('admin.googleContacts.disconnectError', 'Nie udało się odłączyć Google Contacts') }),
})

function disconnect() {
  if (!confirm(t('admin.googleContacts.disconnectConfirm', 'Odłączyć Google Contacts? Będzie trzeba połączyć ponownie, aby importować kontakty.'))) return
  disconnectMutation.mutate()
}

async function loadContacts() {
  if (keywordsList.value.length === 0) return

  isLoadingContacts.value = true
  try {
    const response = await googleContactsApiService.listContacts(keywordsList.value)
    selectableContacts.value = response.contacts.map(contact => ({
      contact,
      selected: true,
      type: contact.suggestedType,
    }))
    totalFetched.value = response.totalFetched
    keywordsUsed.value = keywordsList.value
    searchQuery.value = ''
    matchInName.value = true
    matchInDescription.value = true
    churchProposals.value = []
    personProposals.value = []
    if (response.matchedCount === 0) {
      toast.info(t('admin.googleContacts.noneFound', 'Nie znaleziono kontaktów pasujących do podanych słów kluczowych'))
    }
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.loadContactsError', 'Nie udało się wczytać kontaktów') })
  } finally {
    isLoadingContacts.value = false
  }
}

function contactLabel(contact: IGoogleContactSuggestion): string {
  return contact.displayName ?? contact.organizationName ?? contact.resourceName
}

async function analyzeSelected() {
  const items = selectableContacts.value
    .filter(c => c.selected)
    .map(c => ({ contact: c.contact, type: c.type }))

  if (items.length === 0) return

  isAnalyzing.value = true
  try {
    const response = await googleContactsApiService.analyzeImport({ items })
    candidateTenants.value = response.candidateTenants
    serviceTypes.value = response.serviceTypes

    churchProposals.value = response.churchProposals.map(p => ({
      resourceName: p.resourceName,
      matchType: p.matchType,
      confidence: p.confidence,
      matchedName: p.matchedName,
      skip: false,
      targetTenantId: p.tenantId ?? CREATE_NEW_VALUE,
      name: p.name,
      street: p.street ?? '',
      city: p.city ?? '',
      postalCode: p.postalCode ?? '',
      province: p.province ?? '',
      country: p.country ?? '',
      phone: p.phone ?? '',
      email: p.email ?? '',
    }))

    personProposals.value = response.personProposals.map(p => ({
      resourceName: p.resourceName,
      matchType: p.matchType,
      personId: p.personId,
      matchedName: p.matchedName,
      matchedBy: p.matchedBy,
      forceCreateNew: false,
      skip: false,
      firstName: p.firstName ?? '',
      lastName: p.lastName ?? '',
      email: p.email ?? '',
      phone: p.phone ?? '',
      assignToChurch: false,
      churchId: '',
      serviceTypeId: '',
      customServiceName: '',
    }))
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.analyzeError', 'Nie udało się przeanalizować wybranych kontaktów') })
  } finally {
    isAnalyzing.value = false
  }
}

function buildChurchApplyItems(): IGoogleContactChurchApplyItem[] {
  return churchProposals.value.map((p) => {
    if (p.skip) {
      return { resourceName: p.resourceName, action: 'skip' }
    }
    const action = p.targetTenantId === CREATE_NEW_VALUE ? 'create' : 'update'
    return {
      resourceName: p.resourceName,
      action,
      tenantId: action === 'update' ? p.targetTenantId : undefined,
      name: p.name || undefined,
      street: p.street || undefined,
      city: p.city || undefined,
      postalCode: p.postalCode || undefined,
      province: p.province || undefined,
      country: p.country || undefined,
      phone: p.phone || undefined,
      email: p.email || undefined,
    }
  })
}

function buildPersonApplyItems(): IGoogleContactPersonApplyItem[] {
  return personProposals.value.map((p) => {
    if (p.skip) {
      return { resourceName: p.resourceName, action: 'skip', assignToChurch: false }
    }
    const usePersonId = p.personId && !p.forceCreateNew
    return {
      resourceName: p.resourceName,
      action: usePersonId ? 'update' : 'create',
      personId: usePersonId ? p.personId : undefined,
      firstName: p.firstName || undefined,
      lastName: p.lastName || undefined,
      email: p.email || undefined,
      phone: p.phone || undefined,
      assignToChurch: p.assignToChurch,
      churchId: p.assignToChurch ? p.churchId : undefined,
      serviceTypeId: p.assignToChurch ? (p.serviceTypeId || undefined) : undefined,
      customServiceName: p.assignToChurch ? (p.customServiceName || undefined) : undefined,
    }
  })
}

async function applyImport() {
  isApplying.value = true
  try {
    const result = await googleContactsApiService.applyImport({
      churchItems: buildChurchApplyItems(),
      personItems: buildPersonApplyItems(),
    })
    toast.success(
      `${t('admin.googleContacts.applySuccess', 'Zaimportowano')}: `
      + `${t('admin.googleContacts.churchesCreated', 'zbory utworzone')} ${result.churchesCreated}, `
      + `${t('admin.googleContacts.churchesUpdated', 'zbory zaktualizowane')} ${result.churchesUpdated}, `
      + `${t('admin.googleContacts.personsCreated', 'osoby utworzone')} ${result.personsCreated}, `
      + `${t('admin.googleContacts.personsUpdated', 'osoby zaktualizowane')} ${result.personsUpdated}, `
      + `${t('admin.googleContacts.skippedCount', 'pominięte')} ${result.skipped}`,
    )
    resetLoadedState()
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.applyError', 'Nie udało się zaimportować danych') })
  } finally {
    isApplying.value = false
  }
}

function goBack() {
  router.push({ name: AdminRouteNames.dashboard })
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="Contact"
        :label="t('admin.googleContacts.title', 'Google Contacts')"
        :description="t('admin.googleContacts.subtitle', 'Wczytaj zbory i osoby ze swojej książki kontaktów Google')"
        with-back-button
        @back="goBack"
      />

      <Card>
        <CardHeader>
          <CardTitle>{{ t('admin.googleContacts.connectionTitle', 'Połączenie') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div v-if="isConnectionLoading" class="text-sm text-muted-foreground">
            {{ t('admin.googleContacts.loading', 'Ładowanie...') }}
          </div>
          <div v-else class="flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <Badge :variant="connection?.connected ? 'success-outline' : 'outline'">
                {{ connection?.connected
                  ? t('admin.googleContacts.connected', 'Połączono')
                  : t('admin.googleContacts.notConnected', 'Niepołączono') }}
              </Badge>
              <span v-if="connection?.connected && connection.connectedAt" class="text-sm text-muted-foreground">
                {{ t('admin.googleContacts.connectedAt', 'od') }} {{ new Date(connection.connectedAt).toLocaleDateString() }}
              </span>
            </div>
            <div class="flex gap-2">
              <Button v-if="!connection?.connected" :disabled="isConnecting" @click="connect">
                <Link2 class="size-4" />
                {{ isConnecting
                  ? t('admin.googleContacts.connecting', 'Łączenie...')
                  : t('admin.googleContacts.connect', 'Połącz z Google') }}
              </Button>
              <Button
                v-else
                variant="outline"
                :disabled="disconnectMutation.isPending.value"
                @click="disconnect"
              >
                <Unlink class="size-4" />
                {{ t('admin.googleContacts.disconnect', 'Odłącz') }}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card v-if="connection?.connected">
        <CardHeader>
          <CardTitle v-if="keywordsUsed.length > 0">
            {{ t('admin.googleContacts.contactsTitleWithKeywords', 'Kontakty pasujące do słów') }}: „{{ keywordsUsed.join('”, „') }}”
          </CardTitle>
          <CardTitle v-else>
            {{ t('admin.googleContacts.contactsTitle', 'Kontakty pasujące do słów kluczowych') }}
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-1">
            <Label for="google-contacts-keywords">
              {{ t('admin.googleContacts.keywordsLabel', 'Słowa kluczowe (oddzielone przecinkami)') }}
            </Label>
            <Input
              id="google-contacts-keywords"
              v-model="keywordsInput"
              :placeholder="DEFAULT_KEYWORDS"
            />
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <Button :disabled="isLoadingContacts || keywordsList.length === 0" @click="loadContacts">
              <RefreshCw class="size-4" />
              {{ isLoadingContacts
                ? t('admin.googleContacts.loadingContacts', 'Wczytywanie...')
                : t('admin.googleContacts.loadContacts', 'Wczytaj kontakty') }}
            </Button>
            <span v-if="hasLoadedContacts" class="text-sm text-muted-foreground">
              {{ t('admin.googleContacts.matched', 'Dopasowano') }} {{ selectableContacts.length }} / {{ totalFetched }}
            </span>
          </div>

          <p v-if="hasLoadedContacts && selectableContacts.length === 0" class="text-sm text-muted-foreground">
            {{ t('admin.googleContacts.empty', 'Brak kontaktów pasujących do podanych słów kluczowych') }}
          </p>

          <div v-if="selectableContacts.length > 0" class="space-y-3">
            <div class="flex flex-wrap items-center gap-3">
              <SearchInput
                v-model="searchQuery"
                class="max-w-xs"
                :placeholder="t('admin.googleContacts.searchPlaceholder', 'Szukaj w wczytanych kontaktach...')"
              />
              <label class="flex items-center gap-2 text-sm">
                <Checkbox v-model="matchInName" />
                {{ t('admin.googleContacts.filterInName', 'W nazwie') }}
              </label>
              <label class="flex items-center gap-2 text-sm">
                <Checkbox v-model="matchInDescription" />
                {{ t('admin.googleContacts.filterInDescription', 'W opisie') }}
              </label>
              <span class="text-sm text-muted-foreground">
                {{ t('admin.googleContacts.visibleCount', 'Widoczne') }} {{ filteredContacts.length }} / {{ selectableContacts.length }}
              </span>
            </div>

            <label class="flex items-center gap-2 text-sm">
              <Checkbox :model-value="visibleSelectionState" @update:model-value="toggleVisibleSelection" />
              {{ t('admin.googleContacts.selectVisible', 'Zaznacz/odznacz widoczne') }}
            </label>

            <p v-if="filteredContacts.length === 0" class="text-sm text-muted-foreground">
              {{ t('admin.googleContacts.noVisibleContacts', 'Brak kontaktów pasujących do wyszukiwania/filtrów') }}
            </p>

            <Card v-for="item in filteredContacts" :key="item.contact.resourceName" class="p-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="flex items-start gap-3">
                  <Checkbox v-model="item.selected" class="mt-1" />
                  <div class="space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="font-medium">{{ contactLabel(item.contact) }}</span>
                    </div>
                    <p v-if="item.contact.organizationName && item.contact.displayName" class="text-sm text-muted-foreground">
                      {{ item.contact.organizationName }}
                    </p>
                    <p v-if="item.contact.notes" class="text-sm text-muted-foreground">
                      {{ item.contact.notes }}
                    </p>
                    <div class="flex flex-col gap-1 text-sm text-muted-foreground">
                      <span v-for="email in item.contact.emailAddresses" :key="email" class="flex items-center gap-1">
                        <Mail class="size-3.5" />{{ email }}
                      </span>
                      <span v-for="phone in item.contact.phoneNumbers" :key="phone" class="flex items-center gap-1">
                        <Phone class="size-3.5" />{{ phone }}
                      </span>
                    </div>
                  </div>
                </div>
                <Select v-model="item.type">
                  <SelectTrigger class="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="church">
                      {{ t('admin.googleContacts.typeChurch', 'Zbór') }}
                    </SelectItem>
                    <SelectItem value="person">
                      {{ t('admin.googleContacts.typePerson', 'Osoba') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </Card>

            <Button :disabled="selectedCount === 0 || isAnalyzing" @click="analyzeSelected">
              <Sparkles class="size-4" />
              {{ isAnalyzing
                ? t('admin.googleContacts.analyzing', 'Analizowanie...')
                : t('admin.googleContacts.analyzeSelected', 'Analizuj wybrane') }}
              ({{ selectedCount }})
            </Button>
          </div>
        </CardContent>
      </Card>

      <div v-if="hasProposals" class="space-y-4">
        <Card v-for="proposal in churchProposals" :key="proposal.resourceName">
          <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
            <div class="space-y-1">
              <CardTitle>{{ proposal.name }}</CardTitle>
              <Badge :variant="proposal.matchType === 'matched' ? 'success-outline' : 'primary-outline'">
                {{ proposal.matchType === 'matched'
                  ? `${t('admin.googleContacts.matchedLabel', 'Dopasowano')} (${proposal.confidence}%)`
                  : t('admin.googleContacts.newChurch', 'Nowy zbór') }}
              </Badge>
            </div>
            <label class="flex items-center gap-2 text-sm shrink-0">
              <Checkbox v-model="proposal.skip" />
              {{ t('admin.googleContacts.skip', 'Pomiń') }}
            </label>
          </CardHeader>
          <CardContent v-if="!proposal.skip" class="space-y-4">
            <div class="space-y-2">
              <Label>{{ t('admin.googleContacts.target', 'Dopasowanie do zboru') }}</Label>
              <Select v-model="proposal.targetTenantId">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="CREATE_NEW_VALUE">
                    {{ t('admin.googleContacts.createNewChurch', 'Utwórz nowy zbór') }}
                  </SelectItem>
                  <SelectItem v-for="tenant in candidateTenants" :key="tenant.tenantId" :value="tenant.tenantId">
                    {{ tenant.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.name', 'Nazwa') }}</Label>
                <Input v-model="proposal.name" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.street', 'Ulica') }}</Label>
                <Input v-model="proposal.street" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.city', 'Miasto') }}</Label>
                <Input v-model="proposal.city" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.postalCode', 'Kod pocztowy') }}</Label>
                <Input v-model="proposal.postalCode" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.phone', 'Telefon') }}</Label>
                <Input v-model="proposal.phone" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.email', 'E-mail') }}</Label>
                <Input v-model="proposal.email" />
              </div>
            </div>
            <p class="text-xs text-muted-foreground">
              {{ t('admin.googleContacts.addressHint', 'Adres zostanie zapisany tylko jeśli podano miasto.') }}
            </p>
          </CardContent>
        </Card>

        <Card v-for="proposal in personProposals" :key="proposal.resourceName">
          <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
            <div class="space-y-1">
              <CardTitle>{{ proposal.firstName }} {{ proposal.lastName }}</CardTitle>
              <Badge :variant="proposal.matchType === 'matched' ? 'success-outline' : 'primary-outline'">
                {{ proposal.matchType === 'matched'
                  ? `${t('admin.googleContacts.matchedPersonLabel', 'Dopasowano po')} ${proposal.matchedBy === 'email' ? t('admin.googleContacts.byEmail', 'e-mailu') : t('admin.googleContacts.byPhone', 'telefonie')}: ${proposal.matchedName}`
                  : t('admin.googleContacts.newPerson', 'Nowa osoba') }}
              </Badge>
            </div>
            <label class="flex items-center gap-2 text-sm shrink-0">
              <Checkbox v-model="proposal.skip" />
              {{ t('admin.googleContacts.skip', 'Pomiń') }}
            </label>
          </CardHeader>
          <CardContent v-if="!proposal.skip" class="space-y-4">
            <label v-if="proposal.matchType === 'matched'" class="flex items-center gap-2 text-sm">
              <Checkbox v-model="proposal.forceCreateNew" />
              {{ t('admin.googleContacts.forceCreateNew', 'To inna osoba — utwórz nową zamiast aktualizować dopasowaną') }}
            </label>
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.firstName', 'Imię') }}</Label>
                <Input v-model="proposal.firstName" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.lastName', 'Nazwisko') }}</Label>
                <Input v-model="proposal.lastName" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.email', 'E-mail') }}</Label>
                <Input v-model="proposal.email" />
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.phone', 'Telefon') }}</Label>
                <Input v-model="proposal.phone" />
              </div>
            </div>

            <label class="flex items-center gap-2 text-sm">
              <Checkbox v-model="proposal.assignToChurch" />
              {{ t('admin.googleContacts.assignToChurch', 'Przypisz do zboru') }}
            </label>
            <div v-if="proposal.assignToChurch" class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.church', 'Zbór') }}</Label>
                <Select v-model="proposal.churchId">
                  <SelectTrigger>
                    <SelectValue :placeholder="t('admin.googleContacts.selectChurch', 'Wybierz zbór')" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="tenant in candidateTenants" :key="tenant.tenantId" :value="tenant.tenantId">
                      {{ tenant.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="space-y-1">
                <Label>{{ t('admin.googleContacts.serviceType', 'Rodzaj służby') }}</Label>
                <Select v-model="proposal.serviceTypeId">
                  <SelectTrigger>
                    <SelectValue :placeholder="t('admin.googleContacts.selectServiceType', 'Wybierz służbę')" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="st in serviceTypes" :key="st.id" :value="st.id">
                      {{ st.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="space-y-1 sm:col-span-2">
                <Label>{{ t('admin.googleContacts.customServiceName', 'Lub własna nazwa służby') }}</Label>
                <Input v-model="proposal.customServiceName" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Button :disabled="isApplying" @click="applyImport">
          {{ isApplying
            ? t('admin.googleContacts.applying', 'Zapisywanie...')
            : t('admin.googleContacts.applyImport', 'Importuj do bazy') }}
        </Button>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
