<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { ArrowLeft, Plus, Trash2 } from 'lucide-vue-next'
import { useForm } from 'vee-validate'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { z } from 'zod'
import Button from '@/components/ui/button/Button.vue'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { ICongregationFull } from '../types/congregation.types'
import { CongregationRoutePaths } from '../routes'
import { congregationApiService } from '../services/congregationApiService'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { handleError } = useHandleError()

const congregationId = route.params.id as string
const loading = ref(true)
const congregationFull = ref<ICongregationFull | null>(null)

// Basic info schema
const basicInfoSchema = z.object({
  name: z.string().min(1, t('congregations.edit.nameRequired', 'Nazwa jest wymagana')),
  description: z.string().optional(),
  status: z.enum(['draft', 'published', 'published_unverified', 'need_verification']),
})

// Address schema
const addressSchema = z.object({
  street: z.string().nullable().optional(),
  city: z.string().min(1, t('congregations.edit.address.cityRequired', 'Miasto jest wymagane')),
  postal_code: z.string().nullable().optional(),
  province: z.string().nullable().optional(),
  country: z.string().default('Poland'),
  status: z.enum(['draft', 'published', 'published_unverified']).optional(),
})

// Service time schema
const serviceTimeSchema = z.object({
  day: z.string().min(1, t('congregations.edit.serviceTime.dayRequired', 'Dzień jest wymagany')),
  time: z.string().min(1, t('congregations.edit.serviceTime.timeRequired', 'Godzina jest wymagana')),
  order: z.number().default(0),
})

// Contact person schema
const contactPersonSchema = z.object({
  name: z.string().min(1, t('congregations.edit.contactPerson.nameRequired', 'Imię i nazwisko jest wymagane')),
  title: z.string().nullable().optional(),
  email: z.string().email().nullable().optional().or(z.literal('')),
  phone: z.string().nullable().optional(),
  order: z.number().default(0),
})

// Form schemas
const basicInfoForm = useForm({
  validationSchema: toTypedSchema(basicInfoSchema),
  initialValues: {
    name: '',
    description: '',
    status: 'draft' as const,
  },
})

const addressForm = useForm({
  validationSchema: toTypedSchema(addressSchema),
  initialValues: {
    street: null,
    city: '',
    postal_code: null,
    province: null,
    country: 'Poland',
    status: 'draft' as const,
  },
})

const serviceTimesFormSchema = z.object({
  serviceTimes: z.array(serviceTimeSchema),
})

const serviceTimesForm = useForm({
  validationSchema: toTypedSchema(serviceTimesFormSchema),
  initialValues: {
    serviceTimes: [] as Array<{ day: string; time: string; order: number }>,
  },
})

// Use refs for dynamic arrays since useFieldArray has context issues with multiple forms
const serviceTimeFields = ref<Array<{ key: string; day: string; time: string; order: number }>>([])
const contactPersonFields = ref<Array<{ key: string; name: string; title: string | null; email: string | null; phone: string | null; order: number }>>([])

function pushServiceTime(value: { day: string; time: string; order: number }) {
  serviceTimeFields.value.push({ ...value, key: `st-${Date.now()}-${Math.random()}` })
  serviceTimesForm.setFieldValue('serviceTimes', serviceTimeFields.value.map(f => ({ day: f.day, time: f.time, order: f.order })))
}

function removeServiceTime(index: number) {
  serviceTimeFields.value.splice(index, 1)
  serviceTimesForm.setFieldValue('serviceTimes', serviceTimeFields.value.map(f => ({ day: f.day, time: f.time, order: f.order })))
}

const contactPersonsFormSchema = z.object({
  contactPersons: z.array(contactPersonSchema),
})

const contactPersonsForm = useForm({
  validationSchema: toTypedSchema(contactPersonsFormSchema),
  initialValues: {
    contactPersons: [] as Array<{ name: string; title: string | null; email: string | null; phone: string | null; order: number }>,
  },
})

function pushContactPerson(value: { name: string; title: string | null; email: string | null; phone: string | null; order: number }) {
  contactPersonFields.value.push({ ...value, key: `cp-${Date.now()}-${Math.random()}` })
  contactPersonsForm.setFieldValue('contactPersons', contactPersonFields.value.map(f => ({ name: f.name, title: f.title, email: f.email, phone: f.phone, order: f.order })))
}

function removeContactPerson(index: number) {
  contactPersonFields.value.splice(index, 1)
  contactPersonsForm.setFieldValue('contactPersons', contactPersonFields.value.map(f => ({ name: f.name, title: f.title, email: f.email, phone: f.phone, order: f.order })))
}

// Load congregation data
async function loadCongregation() {
  loading.value = true
  try {
    // Load tenant basic info
    const tenant = await congregationApiService.getTenant(congregationId)
    basicInfoForm.setValues({
      name: tenant.name,
      description: tenant.description || '',
      status: (tenant.status || 'draft') as 'draft' | 'published' | 'published_unverified' | 'need_verification',
    })

    // Load full congregation data
    congregationFull.value = await congregationApiService.getCongregationFull(congregationId)

    if (!congregationFull.value) {
      throw new Error('Failed to load congregation data')
    }

    // Set address form
    if (congregationFull.value.address) {
      addressForm.setValues({
        street: congregationFull.value.address.street,
        city: congregationFull.value.address.city,
        postal_code: congregationFull.value.address.postal_code,
        province: congregationFull.value.address.province,
        country: congregationFull.value.address.country,
        status: congregationFull.value.address.status as 'draft' | 'published' | 'published_unverified',
      })
    }

    // Set service times
    const serviceTimesData = (congregationFull.value.service_times || []).map(st => ({
      day: st.day,
      time: st.time,
      order: st.order,
    }))
    serviceTimesForm.setValues({
      serviceTimes: serviceTimesData,
    })
    serviceTimeFields.value = serviceTimesData.map((st, idx) => ({
      ...st,
      key: `st-${idx}-${st.day}-${st.time}`,
    }))

    // Set contact persons
    const contactPersonsData = (congregationFull.value.contact_persons || []).map(cp => ({
      name: cp.name,
      title: cp.title ?? null,
      email: cp.email ?? null,
      phone: cp.phone ?? null,
      order: cp.order,
    }))
    contactPersonsForm.setValues({
      contactPersons: contactPersonsData,
    })
    contactPersonFields.value = contactPersonsData.map((cp, idx) => ({
      ...cp,
      key: `cp-${idx}-${cp.name}`,
    }))
  } catch (error) {
    console.error('Failed to load congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.loadError', 'Nie udało się załadować danych zboru') })
    router.push(CongregationRoutePaths.list)
  } finally {
    loading.value = false
  }
}

// Save functions
const saveBasicInfo = basicInfoForm.handleSubmit(async (values) => {
  try {
    await congregationApiService.updateCongregation(congregationId, {
      name: values.name,
      description: values.description,
      status: values.status,
    })
    toast.success(t('congregations.edit.basicInfo.saveSuccess', 'Podstawowe informacje zostały zapisane'))
  } catch (error) {
    console.error('Failed to save basic info:', error)
    handleError(error, { setErrors: basicInfoForm.setErrors, fallbackMessage: t('congregations.edit.basicInfo.saveError', 'Nie udało się zapisać podstawowych informacji') })
  }
})

const saveAddress = addressForm.handleSubmit(async (values) => {
  try {
    if (congregationFull.value?.address) {
      await congregationApiService.updateAddress(congregationId, {
        street: values.street,
        city: values.city,
        postal_code: values.postal_code,
        province: values.province,
        country: values.country,
        status: values.status,
      })
    } else {
      await congregationApiService.createOrUpdateAddress(congregationId, {
        street: values.street,
        city: values.city,
        postal_code: values.postal_code,
        province: values.province,
        country: values.country,
        status: values.status,
      })
    }
    toast.success(t('congregations.edit.address.saveSuccess', 'Adres został zapisany'))
    await loadCongregation()
  } catch (error) {
    console.error('Failed to save address:', error)
    handleError(error, { setErrors: addressForm.setErrors, fallbackMessage: t('congregations.edit.address.saveError', 'Nie udało się zapisać adresu') })
  }
})

async function saveServiceTimes() {
  try {
    // Get current service times
    const currentServiceTimes = congregationFull.value?.service_times || []

    // For simplicity, delete all and recreate
    for (const st of currentServiceTimes) {
      await congregationApiService.deleteServiceTime(congregationId, st.id)
    }

    // Create new service times from refs
    for (const st of serviceTimeFields.value) {
      await congregationApiService.createServiceTime(congregationId, {
        day: st.day,
        time: st.time,
        order: st.order,
      })
    }

    toast.success(t('congregations.edit.serviceTimes.saveSuccess', 'Godziny nabożeństw zostały zapisane'))
    await loadCongregation()
  } catch (error) {
    console.error('Failed to save service times:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.serviceTimes.saveError', 'Nie udało się zapisać godzin nabożeństw') })
  }
}

async function saveContactPersons() {
  try {
    // Get current contact persons
    const currentContactPersons = congregationFull.value?.contact_persons || []

    // For simplicity, delete all and recreate
    for (const cp of currentContactPersons) {
      await congregationApiService.deleteContactPerson(congregationId, cp.id)
    }

    // Create new contact persons from refs
    for (const cp of contactPersonFields.value) {
      await congregationApiService.createContactPerson(congregationId, {
        name: cp.name,
        title: cp.title,
        email: cp.email || null,
        phone: cp.phone,
        order: cp.order,
      })
    }

    toast.success(t('congregations.edit.contactPersons.saveSuccess', 'Osoby kontaktowe zostały zapisane'))
    await loadCongregation()
  } catch (error) {
    console.error('Failed to save contact persons:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.contactPersons.saveError', 'Nie udało się zapisać osób kontaktowych') })
  }
}

function addServiceTime() {
  pushServiceTime({ day: '', time: '', order: serviceTimeFields.value.length })
}

function removeServiceTimeAt(index: number) {
  removeServiceTime(index)
}

function addContactPerson() {
  pushContactPerson({ name: '', title: null, email: null, phone: null, order: contactPersonFields.value.length })
}

function removeContactPersonAt(index: number) {
  removeContactPerson(index)
}

onMounted(() => {
  loadCongregation()
})
</script>

<template>
  <AuthenticatedLayout>
    <div v-if="loading" class="flex items-center justify-center min-h-[400px]">
      <p class="text-muted-foreground">
        {{ t('common.loading', 'Ładowanie...') }}
      </p>
    </div>

    <div v-else class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <Button
            variant="ghost"
            size="icon"
            :aria-label="t('common.back', 'Wstecz')"
            @click="router.push(CongregationRoutePaths.list)"
          >
            <ArrowLeft class="size-4" />
          </Button>
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight">
              {{ t('congregations.edit.title', 'Edytuj zbór') }}
            </h1>
            <p class="text-sm text-muted-foreground">
              {{ t('congregations.edit.subtitle', 'Zarządzaj informacjami o zborze') }}
            </p>
          </div>
        </div>
      </div>

      <div class="max-w-4xl mx-auto space-y-6">
        <!-- Basic Info Section -->
        <form class="bg-card border rounded-lg p-6 space-y-6" @submit.prevent="saveBasicInfo">
          <div class="space-y-4">
            <h2 class="text-xl font-semibold">
              {{ t('congregations.edit.basicInfo.title', 'Podstawowe informacje') }}
            </h2>

            <FormField v-slot="{ componentField }" name="name">
              <FormItem>
                <FormLabel required>
                  {{ t('congregations.edit.basicInfo.name', 'Nazwa') }}
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    :placeholder="t('congregations.edit.basicInfo.namePlaceholder', 'Wprowadź nazwę zboru')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="description">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.basicInfo.description', 'Opis') }}
                </FormLabel>
                <FormControl>
                  <Textarea
                    :placeholder="t('congregations.edit.basicInfo.descriptionPlaceholder', 'Wprowadź opis zboru (opcjonalnie)')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="status">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.basicInfo.status', 'Status') }}
                </FormLabel>
                <Select v-bind="componentField">
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="draft">
                      {{ t('congregations.status.draft', 'Szkic') }}
                    </SelectItem>
                    <SelectItem value="published">
                      {{ t('congregations.status.published', 'Opublikowany') }}
                    </SelectItem>
                    <SelectItem value="published_unverified">
                      {{ t('congregations.status.publishedUnverified', 'Opublikowany (niezweryfikowany)') }}
                    </SelectItem>
                    <SelectItem value="need_verification">
                      {{ t('congregations.status.needVerification', 'Wymaga weryfikacji') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            </FormField>
          </div>

          <div class="flex justify-end">
            <Button type="submit">
              {{ t('common.save', 'Zapisz') }}
            </Button>
          </div>
        </form>

        <!-- Address Section -->
        <form class="bg-card border rounded-lg p-6 space-y-6" @submit.prevent="saveAddress">
          <div class="space-y-4">
            <h2 class="text-xl font-semibold">
              {{ t('congregations.edit.address.title', 'Adres') }}
            </h2>

            <FormField v-slot="{ componentField }" name="street">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.address.street', 'Ulica') }}
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    :placeholder="t('congregations.edit.address.streetPlaceholder', 'Wprowadź ulicę')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField v-slot="{ componentField }" name="city">
                <FormItem>
                  <FormLabel required>
                    {{ t('congregations.edit.address.city', 'Miasto') }}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      :placeholder="t('congregations.edit.address.cityPlaceholder', 'Wprowadź miasto')"
                      v-bind="componentField"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>

              <FormField v-slot="{ componentField }" name="postal_code">
                <FormItem>
                  <FormLabel>
                    {{ t('congregations.edit.address.postalCode', 'Kod pocztowy') }}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      :placeholder="t('congregations.edit.address.postalCodePlaceholder', 'Wprowadź kod pocztowy')"
                      v-bind="componentField"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>
            </div>

            <FormField v-slot="{ componentField }" name="province">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.address.province', 'Województwo') }}
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    :placeholder="t('congregations.edit.address.provincePlaceholder', 'Wprowadź województwo')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="country">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.address.country', 'Kraj') }}
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="status">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.address.status', 'Status adresu') }}
                </FormLabel>
                <Select v-bind="componentField">
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="draft">
                      {{ t('congregations.status.draft', 'Szkic') }}
                    </SelectItem>
                    <SelectItem value="published">
                      {{ t('congregations.status.published', 'Opublikowany') }}
                    </SelectItem>
                    <SelectItem value="published_unverified">
                      {{ t('congregations.status.publishedUnverified', 'Opublikowany (niezweryfikowany)') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            </FormField>
          </div>

          <div class="flex justify-end">
            <Button type="submit">
              {{ t('common.save', 'Zapisz') }}
            </Button>
          </div>
        </form>

        <!-- Service Times Section -->
        <form class="bg-card border rounded-lg p-6 space-y-6" @submit.prevent="saveServiceTimes()">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-semibold">
                {{ t('congregations.edit.serviceTimes.title', 'Godziny nabożeństw') }}
              </h2>
              <Button
                type="button"
                variant="outline"
                size="sm"
                @click="addServiceTime"
              >
                <Plus class="size-4" />
                {{ t('common.add', 'Dodaj') }}
              </Button>
            </div>

            <div v-if="serviceTimeFields.length === 0" class="text-sm text-muted-foreground py-4">
              {{ t('congregations.edit.serviceTimes.empty', 'Brak godzin nabożeństw. Kliknij "Dodaj" aby dodać nową.') }}
            </div>

            <div v-else class="space-y-4">
              <div
                v-for="(field, index) in serviceTimeFields"
                :key="field.key"
                class="flex gap-4 items-start p-4 border rounded-lg"
              >
                <div class="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <FormLabel>
                      {{ t('congregations.edit.serviceTime.day', 'Dzień') }}
                    </FormLabel>
                    <Input
                      v-model="field.day"
                      :placeholder="t('congregations.edit.serviceTime.dayPlaceholder', 'np. Niedziela')"
                    />
                  </div>

                  <div>
                    <FormLabel>
                      {{ t('congregations.edit.serviceTime.time', 'Godzina') }}
                    </FormLabel>
                    <Input
                      v-model="field.time"
                      type="time"
                      :placeholder="t('congregations.edit.serviceTime.timePlaceholder', 'np. 10:00')"
                    />
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="shrink-0 mt-8"
                  @click="removeServiceTimeAt(index)"
                >
                  <Trash2 class="size-4" />
                </Button>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <Button type="submit">
              {{ t('common.save', 'Zapisz') }}
            </Button>
          </div>
        </form>

        <!-- Contact Persons Section -->
        <form class="bg-card border rounded-lg p-6 space-y-6" @submit.prevent="saveContactPersons()">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-semibold">
                {{ t('congregations.edit.contactPersons.title', 'Osoby kontaktowe') }}
              </h2>
              <Button
                type="button"
                variant="outline"
                size="sm"
                @click="addContactPerson"
              >
                <Plus class="size-4" />
                {{ t('common.add', 'Dodaj') }}
              </Button>
            </div>

            <div v-if="contactPersonFields.length === 0" class="text-sm text-muted-foreground py-4">
              {{ t('congregations.edit.contactPersons.empty', 'Brak osób kontaktowych. Kliknij "Dodaj" aby dodać nową.') }}
            </div>

            <div v-else class="space-y-4">
              <div
                v-for="(field, index) in contactPersonFields"
                :key="field.key"
                class="p-4 border rounded-lg space-y-4"
              >
                <div class="flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    @click="removeContactPersonAt(index)"
                  >
                    <Trash2 class="size-4" />
                  </Button>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <FormLabel required>
                      {{ t('congregations.edit.contactPerson.name', 'Imię i nazwisko') }}
                    </FormLabel>
                    <Input
                      v-model="field.name"
                      :placeholder="t('congregations.edit.contactPerson.namePlaceholder', 'Wprowadź imię i nazwisko')"
                    />
                  </div>

                  <div>
                    <FormLabel>
                      {{ t('congregations.edit.contactPerson.title', 'Tytuł/Stanowisko') }}
                    </FormLabel>
                    <Input
                      :placeholder="t('congregations.edit.contactPerson.titlePlaceholder', 'np. Pastor')"
                      :model-value="field.title ?? ''"
                      @update:model-value="field.title = (typeof $event === 'string' ? $event : null) || null"
                    />
                  </div>

                  <div>
                    <FormLabel>
                      {{ t('congregations.edit.contactPerson.email', 'Email') }}
                    </FormLabel>
                    <Input
                      type="email"
                      :placeholder="t('congregations.edit.contactPerson.emailPlaceholder', 'Your e-mail address')"
                      :model-value="field.email ?? ''"
                      @update:model-value="field.email = (typeof $event === 'string' ? $event : null) || null"
                    />
                  </div>

                  <div>
                    <FormLabel>
                      {{ t('congregations.edit.contactPerson.phone', 'Telefon') }}
                    </FormLabel>
                    <Input
                      type="tel"
                      :placeholder="t('congregations.edit.contactPerson.phonePlaceholder', '+48 123 456 789')"
                      :model-value="field.phone ?? ''"
                      @update:model-value="field.phone = (typeof $event === 'string' ? $event : null) || null"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <Button type="submit">
              {{ t('common.save', 'Zapisz') }}
            </Button>
          </div>
        </form>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
