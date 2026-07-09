<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Button from '@/components/ui/button/Button.vue'
import Checkbox from '@/components/ui/checkbox/Checkbox.vue'
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

const useCustomService = ref(false)
const createAccount = ref(false)
const form = ref({
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  serviceTypeId: '',
  customServiceName: '',
  description: '',
})

const pastorSlugs = new Set(['mlodszy_pastor', 'pastor', 'senior_pastor'])

const selectedType = computed(() =>
  serviceTypes.value.find(st => st.id === form.value.serviceTypeId),
)

const isPastorType = computed(() =>
  selectedType.value ? pastorSlugs.has(selectedType.value.slug) : false,
)

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
  }
  useCustomService.value = false
  createAccount.value = false
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

    <ul v-else class="space-y-2">
      <li
        v-for="item in assignments"
        :key="item.id"
        class="flex items-start justify-between gap-2 rounded-md border px-3 py-2"
      >
        <div>
          <p class="font-medium">
            {{ personLabel(item) }}
          </p>
          <p class="text-sm text-muted-foreground">
            {{ serviceLabel(item) }}
            <span v-if="item.description"> · {{ item.description }}</span>
          </p>
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
        <Input v-model="form.email" type="email" />
      </div>
      <div class="space-y-1">
        <Label>{{ t('congregations.people.phone', 'Telefon') }}</Label>
        <Input v-model="form.phone" />
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
        <SelectContent>
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
      <Checkbox v-model="createAccount" />
      <Label>
        {{ t('congregations.people.createAccount', 'Utwórz konto użytkownika') }}
        <span v-if="isPastorType" class="text-muted-foreground">
          ({{ t('congregations.people.pastorInactive', 'pastor: konto nieaktywne') }})
        </span>
      </Label>
    </div>

    <Button type="button" @click="addPerson">
      <Plus class="size-4" />
      {{ t('congregations.people.add', 'Dodaj osobę') }}
    </Button>
  </div>
</template>
