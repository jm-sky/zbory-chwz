<script setup lang="ts">
import { Globe, Lock, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Button from '@/components/ui/button/Button.vue'
import Checkbox from '@/components/ui/checkbox/Checkbox.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IServiceAssignment, IServiceType } from '../types/church.types'
import { churchApiService } from '../services/churchApiService'

const { churchId } = defineProps<{ churchId: string }>()

const { t } = useI18n()
const { handleError } = useHandleError()

const assignments = ref<IServiceAssignment[]>([])
const serviceTypes = ref<IServiceType[]>([])
const loading = ref(true)
const savingVisibilityId = ref<string | null>(null)

const useCustomService = ref(false)
const createAccount = ref(false)
const accountRole = ref('member')
const form = ref({
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  serviceTypeId: '',
  customServiceName: '',
  description: '',
  showOnCard: true,
  phonePublic: true,
  emailPublic: false,
})

const pastorSlugs = new Set(['mlodszy_pastor', 'pastor', 'senior_pastor'])

const selectedType = computed(() =>
  serviceTypes.value.find(st => st.id === form.value.serviceTypeId),
)

const isPastorType = computed(() =>
  selectedType.value ? pastorSlugs.has(selectedType.value.slug) : false,
)

const showAccountRoleSelect = computed(() => createAccount.value || isPastorType.value)

const roleOptions = computed(() => {
  const roles = new Set(['member', 'owner'])
  for (const serviceType of serviceTypes.value) {
    if (serviceType.suggestedRole) {
      roles.add(serviceType.suggestedRole)
    }
  }
  return Array.from(roles)
})

const serviceTypesEmpty = computed(() => !loading.value && serviceTypes.value.length === 0)

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

function visibilityTooltip(isPublic: boolean): string {
  return isPublic
    ? t('congregations.people.visibilityPublic', 'Widoczny publicznie')
    : t('congregations.people.visibilityPrivate', 'Ukryty')
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
  form.value = {
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    serviceTypeId: '',
    customServiceName: '',
    description: '',
    showOnCard: true,
    phonePublic: true,
    emailPublic: false,
  }
  useCustomService.value = false
  createAccount.value = false
  accountRole.value = 'member'
}

async function addPerson() {
  try {
    const payload = {
      firstName: form.value.firstName || undefined,
      lastName: form.value.lastName || undefined,
      email: form.value.email || undefined,
      phone: form.value.phone || undefined,
      description: form.value.description || undefined,
      serviceTypeId: useCustomService.value ? undefined : form.value.serviceTypeId || undefined,
      customServiceName: useCustomService.value ? form.value.customServiceName || undefined : undefined,
      createAccount: createAccount.value || isPastorType.value,
      suggestedRole: showAccountRoleSelect.value ? accountRole.value : undefined,
      showOnCard: form.value.showOnCard,
      phonePublic: form.value.phonePublic,
      emailPublic: form.value.emailPublic,
    }
    const created = await churchApiService.createServiceAssignment(churchId, payload)
    assignments.value.push(created)
    resetForm()
    toast.success(t('congregations.people.added', 'Osoba dodana'))
  } catch (error) {
    handleError(error)
  }
}

async function removeAssignment(assignmentId: string) {
  try {
    await churchApiService.deleteServiceAssignment(churchId, assignmentId)
    assignments.value = assignments.value.filter(a => a.id !== assignmentId)
    toast.success(t('congregations.people.removed', 'Usunięto przypisanie'))
  } catch (error) {
    handleError(error)
  }
}

async function updateVisibility(
  assignment: IServiceAssignment,
  field: 'showOnCard' | 'phonePublic' | 'emailPublic',
  value: boolean,
) {
  savingVisibilityId.value = assignment.id
  try {
    const updated = await churchApiService.updateServiceAssignment(churchId, assignment.id, {
      [field]: value,
    })
    const index = assignments.value.findIndex(a => a.id === assignment.id)
    if (index >= 0) {
      assignments.value[index] = updated
    }
  } catch (error) {
    handleError(error)
  } finally {
    savingVisibilityId.value = null
  }
}

watch(selectedType, (serviceType) => {
  if (!serviceType) return
  if (pastorSlugs.has(serviceType.slug)) {
    createAccount.value = true
  }
  if (serviceType.suggestedRole) {
    accountRole.value = serviceType.suggestedRole
  }
})

onMounted(load)
</script>

<template>
  <div class="space-y-4 rounded-lg border p-4">
    <h3 class="text-lg font-semibold">
      {{ t('congregations.people.title', 'Ludzie i służby') }}
    </h3>

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
            <div
              v-if="item.person?.phone"
              class="flex max-w-sm items-center"
            >
              <span class="flex-1 rounded-l-md border border-r-0 bg-muted/40 px-3 py-2 text-sm">
                {{ item.person.phone }}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="rounded-l-none border-l-0 px-2.5"
                    :disabled="savingVisibilityId === item.id"
                    v-tooltip="visibilityTooltip(item.phonePublic)"
                  >
                    <Globe v-if="item.phonePublic" class="size-4" />
                    <Lock v-else class="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click="updateVisibility(item, 'phonePublic', true)">
                    <Globe class="size-4" />
                    {{ t('congregations.people.visibilityPublic', 'Widoczny publicznie') }}
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="updateVisibility(item, 'phonePublic', false)">
                    <Lock class="size-4" />
                    {{ t('congregations.people.visibilityPrivate', 'Ukryty') }}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div
              v-if="item.person?.email"
              class="flex max-w-sm items-center"
            >
              <span class="flex-1 truncate rounded-l-md border border-r-0 bg-muted/40 px-3 py-2 text-sm">
                {{ item.person.email }}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="rounded-l-none border-l-0 px-2.5"
                    :disabled="savingVisibilityId === item.id"
                    v-tooltip="visibilityTooltip(item.emailPublic)"
                  >
                    <Globe v-if="item.emailPublic" class="size-4" />
                    <Lock v-else class="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click="updateVisibility(item, 'emailPublic', true)">
                    <Globe class="size-4" />
                    {{ t('congregations.people.visibilityPublic', 'Widoczny publicznie') }}
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="updateVisibility(item, 'emailPublic', false)">
                    <Lock class="size-4" />
                    {{ t('congregations.people.visibilityPrivate', 'Ukryty') }}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <Checkbox
              :model-value="item.showOnCard"
              :disabled="savingVisibilityId === item.id"
              @update:model-value="updateVisibility(item, 'showOnCard', $event === true)"
            />
            <span>{{ t('congregations.people.showOnCard', 'Widoczne na karcie zboru') }}</span>
          </label>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          @click="removeAssignment(item.id)"
        >
          <Trash2 class="size-4" />
        </Button>
      </li>
      <li v-if="assignments.length === 0" class="text-sm text-muted-foreground">
        {{ t('congregations.people.empty', 'Brak przypisań') }}
      </li>
    </ul>

    <div class="grid gap-3 sm:grid-cols-2">
      <div class="space-y-1">
        <Label>{{ t('congregations.people.firstName', 'Imię') }}</Label>
        <Input v-model="form.firstName" />
      </div>
      <div class="space-y-1">
        <Label>{{ t('congregations.people.lastName', 'Nazwisko') }}</Label>
        <Input v-model="form.lastName" />
      </div>
      <div class="space-y-1">
        <Label>{{ t('congregations.people.email', 'E-mail') }}</Label>
        <div class="flex">
          <Input
            v-model="form.email"
            type="email"
            class="rounded-r-none focus-visible:z-10"
          />
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                type="button"
                variant="outline"
                class="rounded-l-none border-l-0 shrink-0 px-2.5"
                v-tooltip="visibilityTooltip(form.emailPublic)"
              >
                <Globe v-if="form.emailPublic" class="size-4" />
                <Lock v-else class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="form.emailPublic = true">
                <Globe class="size-4" />
                {{ t('congregations.people.visibilityPublic', 'Widoczny publicznie') }}
              </DropdownMenuItem>
              <DropdownMenuItem @click="form.emailPublic = false">
                <Lock class="size-4" />
                {{ t('congregations.people.visibilityPrivate', 'Ukryty') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div class="space-y-1">
        <Label>{{ t('congregations.people.phone', 'Telefon') }}</Label>
        <div class="flex">
          <Input
            v-model="form.phone"
            class="rounded-r-none focus-visible:z-10"
          />
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                type="button"
                variant="outline"
                class="rounded-l-none border-l-0 shrink-0 px-2.5"
                v-tooltip="visibilityTooltip(form.phonePublic)"
              >
                <Globe v-if="form.phonePublic" class="size-4" />
                <Lock v-else class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="form.phonePublic = true">
                <Globe class="size-4" />
                {{ t('congregations.people.visibilityPublic', 'Widoczny publicznie') }}
              </DropdownMenuItem>
              <DropdownMenuItem @click="form.phonePublic = false">
                <Lock class="size-4" />
                {{ t('congregations.people.visibilityPrivate', 'Ukryty') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
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

    <label class="flex items-center gap-2 text-sm">
      <Checkbox v-model="form.showOnCard" />
      <span>{{ t('congregations.people.showOnCard', 'Widoczne na karcie zboru') }}</span>
    </label>

    <div class="flex items-center gap-2">
      <Checkbox v-model="createAccount" />
      <Label>
        {{ t('congregations.people.createAccount', 'Utwórz konto użytkownika') }}
        <span v-if="isPastorType" class="text-muted-foreground">
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
  </div>
</template>
