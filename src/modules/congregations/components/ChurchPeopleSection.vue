<script setup lang="ts">
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Button from '@/components/ui/button/Button.vue'
import Checkbox from '@/components/ui/checkbox/Checkbox.vue'
import {
  Dialog,
  DialogContent,
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
import { Textarea } from '@/components/ui/textarea'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import PersonLinkedBadge from '@/shared/components/PersonLinkedBadge.vue'
import PersonSuggestionsList from '@/shared/components/PersonSuggestionsList.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import { usePersonAutocomplete } from '@/shared/composables/usePersonAutocomplete'
import type { IServiceAssignment, IServiceType } from '../types/church.types'
import { churchApiService } from '../services/churchApiService'
import {
  CHURCH_ACL_ROLES,
  type ChurchAclRole,
  DEFAULT_CARD_VISIBILITY,
  DEFAULT_EMAIL_VISIBILITY,
  DEFAULT_PHONE_VISIBILITY,
  ELEVATED_ACL_ROLES,
  type VisibilityLevel,
} from '../types/visibility.types'
import ContactFieldWithVisibility from './ContactFieldWithVisibility.vue'
import VisibilityLevelSelect from './VisibilityLevelSelect.vue'

const { churchId } = defineProps<{ churchId: string }>()

const { t } = useI18n()
const authStore = useAuthStore()
const { handleError } = useHandleError()

const assignments = ref<IServiceAssignment[]>([])
const serviceTypes = ref<IServiceType[]>([])
const loading = ref(true)
const savingId = ref<string | null>(null)

const useCustomService = ref(false)
const createAccount = ref(false)
const accountRole = ref<'none' | ChurchAclRole>('none')
const form = ref(createEmptyForm())
const personAutocomplete = usePersonAutocomplete()

const editDialogOpen = ref(false)
const editingId = ref<string | null>(null)
const editUseCustomService = ref(false)
const editForm = ref(createEmptyForm())
const savingEdit = ref(false)

const pastorSlugs = new Set(['mlodszy_pastor', 'pastor', 'senior_pastor'])

function createEmptyForm() {
  return {
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    serviceTypeId: '',
    customServiceName: '',
    description: '',
    cardVisibility: DEFAULT_CARD_VISIBILITY,
    phoneVisibility: DEFAULT_PHONE_VISIBILITY,
    emailVisibility: DEFAULT_EMAIL_VISIBILITY,
  }
}

const selectedType = computed(() =>
  serviceTypes.value.find(st => st.id === form.value.serviceTypeId),
)

const isPastorType = computed(() =>
  selectedType.value ? pastorSlugs.has(selectedType.value.slug) : false,
)

const showAccountRoleSelect = computed(() => createAccount.value)

const canGrantElevatedRoles = computed<boolean>(
  () => !!(authStore.user?.isAdmin || authStore.user?.isOwner),
)

const roleOptions = computed<Array<'none' | ChurchAclRole>>(() => {
  const roles = canGrantElevatedRoles.value
    ? CHURCH_ACL_ROLES
    : CHURCH_ACL_ROLES.filter(role => !ELEVATED_ACL_ROLES.includes(role))
  return ['none', ...roles]
})

const serviceTypesEmpty = computed(() => !loading.value && serviceTypes.value.length === 0)

const showOnCardAdd = computed<boolean>({
  get: () => form.value.cardVisibility === 'public',
  set: (checked: boolean) => {
    form.value.cardVisibility = checked ? 'public' : 'hidden'
  },
})

function isShownOnCard(assignment: IServiceAssignment): boolean {
  return assignment.cardVisibility === 'public'
}

async function toggleShowOnCard(assignment: IServiceAssignment, checked: boolean | 'indeterminate') {
  if (checked === 'indeterminate') return
  await updateAssignmentVisibility(
    assignment,
    'cardVisibility',
    checked ? 'public' : 'hidden',
  )
}

function personLabel(assignment: IServiceAssignment): string {
  const p = assignment.person
  if (!p) return '—'
  const name = [p.firstName, p.lastName].filter(Boolean).join(' ')
  return name || p.email || '—'
}

function serviceLabel(assignment: IServiceAssignment): string {
  if (assignment.serviceType) return assignment.serviceType.name
  return assignment.customServiceName || '—'
}

function roleLabel(role: string): string {
  return t(`congregations.people.roles.${role}`, role)
}

function isGrantableRole(role: string): role is ChurchAclRole {
  return roleOptions.value.includes(role as ChurchAclRole)
}

function visibilityPayload(formData: ReturnType<typeof createEmptyForm>) {
  return {
    cardVisibility: formData.cardVisibility,
    phoneVisibility: formData.phoneVisibility,
    emailVisibility: formData.emailVisibility,
  }
}

async function load() {
  loading.value = true
  try {
    const [types, list] = await Promise.all([
      churchApiService.listServiceTypes(),
      churchApiService.listServiceAssignments(churchId),
    ])
    serviceTypes.value = types.filter(st => st.scopeType === 'church')
    assignments.value = list
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = createEmptyForm()
  useCustomService.value = false
  createAccount.value = false
  accountRole.value = 'none'
  personAutocomplete.reset()
}

function onPersonFieldChange(field: 'firstName' | 'lastName' | 'email' | 'phone', value: string) {
  personAutocomplete.handleFieldChange(field, value)
}

function onSelectPerson(person: Parameters<typeof personAutocomplete.selectPerson>[0]) {
  const filled = personAutocomplete.selectPerson(person)
  form.value.firstName = filled.firstName
  form.value.lastName = filled.lastName
  form.value.email = filled.email
  form.value.phone = filled.phone
}

async function addPerson() {
  try {
    const payload = {
      personId: personAutocomplete.linkedPersonId.value ?? undefined,
      firstName: form.value.firstName || undefined,
      lastName: form.value.lastName || undefined,
      email: form.value.email || undefined,
      phone: form.value.phone || undefined,
      description: form.value.description || undefined,
      serviceTypeId: useCustomService.value ? undefined : form.value.serviceTypeId || undefined,
      customServiceName: useCustomService.value ? form.value.customServiceName || undefined : undefined,
      createAccount: createAccount.value,
      suggestedRole: showAccountRoleSelect.value && accountRole.value !== 'none'
        ? accountRole.value
        : undefined,
      ...visibilityPayload(form.value),
    }
    const created = await churchApiService.createServiceAssignment(churchId, payload)
    assignments.value.push(created)
    resetForm()
    toast.success(t('congregations.people.added', 'Osoba dodana'))
  } catch (error) {
    handleError(error)
  }
}

function openEdit(item: IServiceAssignment) {
  editingId.value = item.id
  editUseCustomService.value = !item.serviceTypeId && !!item.customServiceName
  editForm.value = {
    firstName: item.person?.firstName ?? '',
    lastName: item.person?.lastName ?? '',
    email: item.person?.email ?? '',
    phone: item.person?.phone ?? '',
    serviceTypeId: item.serviceTypeId ?? '',
    customServiceName: item.customServiceName ?? '',
    description: item.description ?? '',
    cardVisibility: item.cardVisibility as VisibilityLevel,
    phoneVisibility: item.phoneVisibility as VisibilityLevel,
    emailVisibility: item.emailVisibility as VisibilityLevel,
  }
  editDialogOpen.value = true
}

async function saveEdit() {
  if (!editingId.value) return
  savingEdit.value = true
  try {
    const updated = await churchApiService.updateServiceAssignment(churchId, editingId.value, {
      firstName: editForm.value.firstName || undefined,
      lastName: editForm.value.lastName || undefined,
      email: editForm.value.email || undefined,
      phone: editForm.value.phone || undefined,
      description: editForm.value.description || undefined,
      serviceTypeId: editUseCustomService.value ? undefined : editForm.value.serviceTypeId || undefined,
      customServiceName: editUseCustomService.value ? editForm.value.customServiceName || undefined : undefined,
      ...visibilityPayload(editForm.value),
    })
    const index = assignments.value.findIndex(a => a.id === editingId.value)
    if (index >= 0) {
      assignments.value[index] = updated
    }
    editDialogOpen.value = false
    editingId.value = null
    toast.success(t('congregations.people.updated', 'Zapisano zmiany'))
  } catch (error) {
    handleError(error)
  } finally {
    savingEdit.value = false
  }
}

async function removeAssignment(assignmentId: string) {
  if (!confirm(t('congregations.people.removeConfirm'))) return
  try {
    await churchApiService.deleteServiceAssignment(churchId, assignmentId)
    assignments.value = assignments.value.filter(a => a.id !== assignmentId)
    toast.success(t('congregations.people.removed', 'Usunięto przypisanie'))
  } catch (error) {
    handleError(error)
  }
}

async function updateAssignmentVisibility(
  assignment: IServiceAssignment,
  field: 'cardVisibility' | 'phoneVisibility' | 'emailVisibility',
  level: VisibilityLevel,
) {
  savingId.value = assignment.id
  try {
    const updated = await churchApiService.updateServiceAssignment(churchId, assignment.id, {
      [field]: level,
    })
    const index = assignments.value.findIndex(a => a.id === assignment.id)
    if (index >= 0) {
      assignments.value[index] = updated
    }
  } catch (error) {
    handleError(error)
  } finally {
    savingId.value = null
  }
}

watch(selectedType, (serviceType) => {
  if (!serviceType) return
  if (pastorSlugs.has(serviceType.slug)) {
    createAccount.value = true
  }
  if (serviceType.suggestedRole && isGrantableRole(serviceType.suggestedRole)) {
    accountRole.value = serviceType.suggestedRole
  } else {
    accountRole.value = 'none'
  }
})

onMounted(load)
</script>

<template>
  <div class="space-y-4 rounded-lg border p-4">
    <h3 class="text-lg font-semibold">
      {{ t('congregations.people.title', 'Ludzie i służby') }}
    </h3>
    <p class="text-sm text-muted-foreground">
      {{ t('congregations.people.showOnCardHint', 'Zaznaczone osoby są widoczne na publicznej karcie zboru') }}
    </p>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>

    <p
      v-else-if="serviceTypesEmpty"
      class="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100"
    >
      {{ t('congregations.people.noServiceTypes', 'Brak typów służb w bazie. Uruchom: python -m cli db churches-backfill') }}
    </p>

    <ul v-if="!loading" class="space-y-2">
      <li
        v-for="item in assignments"
        :key="item.id"
        class="flex items-start justify-between gap-2 rounded-md border px-3 py-2"
      >
        <div class="min-w-0 flex-1 space-y-2">
          <div>
            <p class="font-medium">
              {{ personLabel(item) }}
            </p>
            <p class="text-sm text-muted-foreground">
              {{ serviceLabel(item) }}
              <span v-if="item.description"> · {{ item.description }}</span>
            </p>
          </div>
          <div class="space-y-2">
            <div v-if="item.person?.phone" class="max-w-md space-y-1">
              <Label class="text-xs text-muted-foreground">
                {{ t('congregations.people.phone', 'Telefon') }}
              </Label>
              <ContactFieldWithVisibility
                :model-value="item.person.phone"
                :visibility="item.phoneVisibility as VisibilityLevel"
                readonly
                :disabled="savingId === item.id"
                @update:visibility="updateAssignmentVisibility(item, 'phoneVisibility', $event)"
              />
            </div>
            <div v-if="item.person?.email" class="max-w-md space-y-1">
              <Label class="text-xs text-muted-foreground">
                {{ t('congregations.people.email', 'E-mail') }}
              </Label>
              <ContactFieldWithVisibility
                :model-value="item.person.email"
                :visibility="item.emailVisibility as VisibilityLevel"
                type="email"
                readonly
                :disabled="savingId === item.id"
                @update:visibility="updateAssignmentVisibility(item, 'emailVisibility', $event)"
              />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox
              :model-value="isShownOnCard(item)"
              :disabled="savingId === item.id"
              @update:model-value="toggleShowOnCard(item, $event)"
            />
            <Label class="text-sm">
              {{ t('congregations.people.showOnCard', 'Pokaz na wizytówce') }}
            </Label>
          </div>
        </div>
        <div class="flex shrink-0 gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            @click="openEdit(item)"
          >
            <Pencil class="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            @click="removeAssignment(item.id)"
          >
            <Trash2 class="size-4" />
          </Button>
        </div>
      </li>
      <li v-if="assignments.length === 0" class="text-sm text-muted-foreground">
        {{ t('congregations.people.empty', 'Brak przypisań') }}
      </li>
    </ul>

    <PersonLinkedBadge
      v-if="personAutocomplete.linkedPersonId.value"
      @unlink="personAutocomplete.unlink()"
    />
    <div class="grid gap-3 sm:grid-cols-2">
      <div class="relative space-y-1">
        <Label>{{ t('congregations.people.firstName', 'Imię') }}</Label>
        <Input
          v-model="form.firstName"
          @update:model-value="onPersonFieldChange('firstName', String($event))"
          @blur="personAutocomplete.closeSuggestions()"
        />
        <PersonSuggestionsList
          v-if="personAutocomplete.activeField.value === 'firstName'"
          :suggestions="personAutocomplete.suggestions.value"
          @select="onSelectPerson"
        />
      </div>
      <div class="relative space-y-1">
        <Label>{{ t('congregations.people.lastName', 'Nazwisko') }}</Label>
        <Input
          v-model="form.lastName"
          @update:model-value="onPersonFieldChange('lastName', String($event))"
          @blur="personAutocomplete.closeSuggestions()"
        />
        <PersonSuggestionsList
          v-if="personAutocomplete.activeField.value === 'lastName'"
          :suggestions="personAutocomplete.suggestions.value"
          @select="onSelectPerson"
        />
      </div>
      <div class="relative space-y-1">
        <Label>{{ t('congregations.people.email', 'E-mail') }}</Label>
        <ContactFieldWithVisibility
          v-model="form.email"
          v-model:visibility="form.emailVisibility"
          type="email"
          @update:model-value="onPersonFieldChange('email', String($event))"
          @blur="personAutocomplete.closeSuggestions()"
        />
        <PersonSuggestionsList
          v-if="personAutocomplete.activeField.value === 'email'"
          :suggestions="personAutocomplete.suggestions.value"
          @select="onSelectPerson"
        />
      </div>
      <div class="relative space-y-1">
        <Label>{{ t('congregations.people.phone', 'Telefon') }}</Label>
        <ContactFieldWithVisibility
          v-model="form.phone"
          v-model:visibility="form.phoneVisibility"
          @update:model-value="onPersonFieldChange('phone', String($event))"
          @blur="personAutocomplete.closeSuggestions()"
        />
        <PersonSuggestionsList
          v-if="personAutocomplete.activeField.value === 'phone'"
          :suggestions="personAutocomplete.suggestions.value"
          @select="onSelectPerson"
        />
      </div>
    </div>

    <div class="flex items-center gap-2">
      <Checkbox v-model="useCustomService" />
      <Label>{{ t('congregations.people.customService', 'Inna służba') }}</Label>
    </div>

    <div v-if="useCustomService" class="space-y-1">
      <Label>{{ t('congregations.people.customServiceName', 'Nazwa służby') }}</Label>
      <Input v-model="form.customServiceName" />
    </div>
    <div v-else class="space-y-1">
      <Label>{{ t('congregations.people.service', 'Służba') }}</Label>
      <Select v-model="form.serviceTypeId">
        <SelectTrigger>
          <SelectValue :placeholder="t('congregations.people.servicePlaceholder', 'Wybierz służbę')" />
        </SelectTrigger>
        <SelectContent class="z-[100]">
          <SelectItem
            v-for="st in serviceTypes"
            :key="st.id"
            :value="st.id"
          >
            {{ st.name }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div class="space-y-1">
      <Label>{{ t('congregations.people.description', 'Opis') }}</Label>
      <Textarea v-model="form.description" rows="2" />
    </div>

    <div class="flex items-center gap-2">
      <Checkbox v-model="showOnCardAdd" />
      <Label>
        {{ t('congregations.people.showOnCard', 'Pokaz na wizytówce') }}
      </Label>
    </div>

    <div class="flex items-center gap-2">
      <Checkbox v-model="createAccount" />
      <Label>
        {{ t('congregations.people.createAccount', 'Utwórz konto użytkownika') }}
        <span v-if="isPastorType && createAccount" class="text-muted-foreground">
          ({{ t('congregations.people.pastorInactive', 'pastor: konto nieaktywne') }})
        </span>
      </Label>
    </div>

    <div v-if="showAccountRoleSelect" class="space-y-1">
      <Label>{{ t('congregations.people.accountRole', 'Uprawnienia') }}</Label>
      <Select v-model="accountRole">
        <SelectTrigger>
          <SelectValue :placeholder="t('congregations.people.accountRolePlaceholder', 'Wybierz uprawnienia')" />
        </SelectTrigger>
        <SelectContent class="z-[100]">
          <SelectItem
            v-for="role in roleOptions"
            :key="role"
            :value="role"
          >
            {{ roleLabel(role) }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <Button type="button" @click="addPerson">
      <Plus class="size-4" />
      {{ t('congregations.people.add', 'Dodaj osobę') }}
    </Button>

    <Dialog v-model:open="editDialogOpen">
      <DialogContent class="max-h-[85vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {{ t('congregations.people.editTitle', 'Edytuj osobę') }}
          </DialogTitle>
        </DialogHeader>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="space-y-1">
            <Label>{{ t('congregations.people.firstName', 'Imię') }}</Label>
            <Input v-model="editForm.firstName" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('congregations.people.lastName', 'Nazwisko') }}</Label>
            <Input v-model="editForm.lastName" />
          </div>
          <div class="space-y-1 sm:col-span-2">
            <Label>{{ t('congregations.people.email', 'E-mail') }}</Label>
            <ContactFieldWithVisibility
              v-model="editForm.email"
              v-model:visibility="editForm.emailVisibility"
              type="email"
            />
          </div>
          <div class="space-y-1 sm:col-span-2">
            <Label>{{ t('congregations.people.phone', 'Telefon') }}</Label>
            <ContactFieldWithVisibility
              v-model="editForm.phone"
              v-model:visibility="editForm.phoneVisibility"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Checkbox v-model="editUseCustomService" />
          <Label>{{ t('congregations.people.customService', 'Inna służba') }}</Label>
        </div>

        <div v-if="editUseCustomService" class="space-y-1">
          <Label>{{ t('congregations.people.customServiceName', 'Nazwa służby') }}</Label>
          <Input v-model="editForm.customServiceName" />
        </div>
        <div v-else class="space-y-1">
          <Label>{{ t('congregations.people.service', 'Służba') }}</Label>
          <Select v-model="editForm.serviceTypeId">
            <SelectTrigger>
              <SelectValue :placeholder="t('congregations.people.servicePlaceholder', 'Wybierz służbę')" />
            </SelectTrigger>
            <SelectContent class="z-[100]">
              <SelectItem
                v-for="st in serviceTypes"
                :key="st.id"
                :value="st.id"
              >
                {{ st.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-1">
          <Label>{{ t('congregations.people.description', 'Opis') }}</Label>
          <Textarea v-model="editForm.description" rows="2" />
        </div>

        <VisibilityLevelSelect
          v-model="editForm.cardVisibility"
          :label="t('congregations.people.visibilityTitle', 'Widoczność na karcie zboru')"
        />

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            @click="editDialogOpen = false"
          >
            {{ t('common.cancel', 'Anuluj') }}
          </Button>
          <Button
            type="button"
            :disabled="savingEdit"
            @click="saveEdit"
          >
            {{ t('common.save', 'Zapisz') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
