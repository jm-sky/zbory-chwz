<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { toTypedSchema } from '@vee-validate/zod'
import { ArrowLeft, Plus, Trash2 } from 'lucide-vue-next'
import { useForm } from 'vee-validate'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { z } from 'zod'
import Button from '@/components/ui/button/Button.vue'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
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
import { useHandleError } from '@/shared/composables/useHandleError'
import { logSafeError } from '@/shared/utils/logSafeError'
import type { ICongregationFull } from '../types/congregation.types'
import ChangeHistorySection from '../components/ChangeHistorySection.vue'
import ChurchBranchesSection from '../components/ChurchBranchesSection.vue'
import ChurchPeopleSection from '../components/ChurchPeopleSection.vue'
import AddressMapPicker from '../components/map/AddressMapPicker.vue'
import ShareLinksSection from '../components/ShareLinksSection.vue'
import { CongregationRoutePaths } from '../routes'
import { congregationApiService } from '../services/congregationApiService'
import {
  countryOptions,
  DEFAULT_COUNTRY_CODE,
  provinceLabel,
  provincesForCountry,
} from '../utils/geo'

const route = useRoute()
const router = useRouter()
const { locale, t } = useI18n()
const { handleError } = useHandleError()
const queryClient = useQueryClient()

const congregationId = route.params.id as string
const loading = ref(true)
const congregationFull = ref<ICongregationFull | null>(null)

// Combined schema for all form fields
const formSchema = z.object({
  // Basic info
  name: z.string().min(1, t('congregations.edit.nameRequired', 'Nazwa jest wymagana')),
  description: z.string().optional(),
  status: z.enum(['draft', 'published', 'published_unverified', 'need_verification']),
  // Address
  street: z.string().nullable().optional(),
  city: z.string().min(1, t('congregations.edit.address.cityRequired', 'Miasto jest wymagane')),
  postal_code: z.string().nullable().optional(),
  province: z.string().nullable().optional(),
  country: z.string().default(DEFAULT_COUNTRY_CODE),
  website: z.string().nullable().optional(),
  email: z.string().email(t('congregations.edit.address.emailInvalid', 'Nieprawidłowy adres e-mail')).or(z.literal('')).nullable().optional(),
  iban: z.string().nullable().optional(),
  latitude: z.number().min(-90).max(90).nullable().optional(),
  longitude: z.number().min(-180).max(180).nullable().optional(),
  address_status: z.enum(['draft', 'published', 'published_unverified']).optional(),
})

// Single form instance for all fields
const form = useForm({
  validationSchema: toTypedSchema(formSchema),
  initialValues: {
    name: '',
    description: '',
    status: 'draft' as const,
    street: null,
    city: '',
    postal_code: null,
    province: null,
    country: DEFAULT_COUNTRY_CODE,
    website: null,
    email: null,
    iban: null,
    latitude: null,
    longitude: null,
    address_status: 'draft' as const,
  },
})

const latitudeModel = computed<number | null>({
  get: () => form.values.latitude ?? null,
  set: value => form.setFieldValue('latitude', value),
})
const longitudeModel = computed<number | null>({
  get: () => form.values.longitude ?? null,
  set: value => form.setFieldValue('longitude', value),
})

// The shadcn Input component's modelValue doesn't accept null, so the manual
// coordinate inputs go through a small null<->undefined adapter.
const latitudeInputModel = computed<number | undefined>({
  get: () => latitudeModel.value ?? undefined,
  set: value => (latitudeModel.value = value ?? null),
})
const longitudeInputModel = computed<number | undefined>({
  get: () => longitudeModel.value ?? undefined,
  set: value => (longitudeModel.value = value ?? null),
})

const geocoding = ref(false)

async function geocodeAddress(): Promise<void> {
  geocoding.value = true
  try {
    const result = await congregationApiService.geocodeAddress(congregationId, {
      street: form.values.street,
      city: form.values.city ?? '',
      postal_code: form.values.postal_code,
      province: form.values.province,
      country: form.values.country,
    })
    if (result.confidence === 'not_found' || result.latitude == null || result.longitude == null) {
      toast.error(t('congregations.edit.address.geocodeNotFound'))
      return
    }
    form.setFieldValue('latitude', result.latitude)
    form.setFieldValue('longitude', result.longitude)
    toast.success(t('congregations.edit.address.geocodeSuccess'))
  } catch (error) {
    logSafeError('Failed to geocode address:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.address.geocodeError') })
  } finally {
    geocoding.value = false
  }
}

const countries = computed<Array<{ code: string; label: string }>>(() =>
  countryOptions(locale.value),
)

// Only Poland has a defined voivodeship list; elsewhere the field stays empty.
const provinces = computed<readonly string[]>(() =>
  provincesForCountry(form.values.country ?? DEFAULT_COUNTRY_CODE),
)

// The backend rejects a province that does not belong to the selected country.
watch(provinces, (available) => {
  const current = form.values.province
  if (current && !available.includes(current)) {
    form.setFieldValue('province', null)
  }
})

// Use refs for dynamic arrays since they're not part of the main form
const serviceTimeFields = ref<Array<{ key: string; id?: string; day: string; time: string; description: string; order: number }>>([])
// Ids of pre-existing service times removed by the user, applied as deletes on save
const deletedServiceTimeIds = ref<string[]>([])

function pushServiceTime(value: { id?: string; day: string; time: string; description: string; order: number }) {
  serviceTimeFields.value.push({ ...value, key: `st-${value.id ?? `${Date.now()}-${Math.random()}`}` })
}

function removeServiceTime(index: number) {
  const [removed] = serviceTimeFields.value.splice(index, 1)
  if (removed?.id) {
    deletedServiceTimeIds.value.push(removed.id)
  }
}

// Load congregation data
async function loadCongregation() {
  loading.value = true
  try {
    // Load tenant basic info
    const tenant = await congregationApiService.getTenant(congregationId)

    // Load full congregation data
    congregationFull.value = await congregationApiService.getCongregationFull(congregationId)

    if (!congregationFull.value) {
      throw new Error('Failed to load congregation data')
    }

    // Set all form values at once
    form.setValues({
      name: tenant.name,
      description: tenant.description || '',
      status: (tenant.status || 'draft') as 'draft' | 'published' | 'published_unverified' | 'need_verification',
      street: congregationFull.value.address?.street ?? null,
      city: congregationFull.value.address?.city ?? '',
      postal_code: congregationFull.value.address?.postal_code ?? null,
      province: congregationFull.value.address?.province ?? null,
      country: congregationFull.value.address?.country ?? DEFAULT_COUNTRY_CODE,
      website: congregationFull.value.address?.website ?? null,
      email: congregationFull.value.address?.email ?? null,
      iban: congregationFull.value.address?.iban ?? null,
      latitude: congregationFull.value.address?.latitude ?? null,
      longitude: congregationFull.value.address?.longitude ?? null,
      address_status: (congregationFull.value.address?.status as 'draft' | 'published' | 'published_unverified') ?? 'draft',
    })

    // Set service times
    serviceTimeFields.value = (congregationFull.value.service_times || []).map(st => ({
      key: `st-${st.id}`,
      id: st.id,
      day: st.day,
      time: st.time,
      description: st.description ?? '',
      order: st.order,
    }))
    deletedServiceTimeIds.value = []
  } catch (error) {
    logSafeError('Failed to load congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.loadError', 'Nie udało się załadować danych zboru') })
    router.push(CongregationRoutePaths.list)
  } finally {
    loading.value = false
  }
}

// Save functions
const saveBasicInfo = form.handleSubmit(async (values) => {
  try {
    await congregationApiService.updateCongregation(congregationId, {
      name: values.name,
      description: values.description,
      status: values.status,
    })
    toast.success(t('congregations.edit.basicInfo.saveSuccess', 'Podstawowe informacje zostały zapisane'))
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
  } catch (error) {
    logSafeError('Failed to save basic info:', error)
    handleError(error, { setErrors: form.setErrors, fallbackMessage: t('congregations.edit.basicInfo.saveError', 'Nie udało się zapisać podstawowych informacji') })
  }
})

const saveAddress = form.handleSubmit(async (values) => {
  try {
    if (congregationFull.value?.address) {
      await congregationApiService.updateAddress(congregationId, {
        street: values.street,
        city: values.city,
        postal_code: values.postal_code,
        province: values.province,
        country: values.country,
        website: values.website || null,
        email: values.email || null,
        iban: values.iban || null,
        latitude: values.latitude,
        longitude: values.longitude,
        status: values.address_status,
      })
    } else {
      await congregationApiService.createOrUpdateAddress(congregationId, {
        street: values.street,
        city: values.city,
        postal_code: values.postal_code,
        province: values.province,
        country: values.country,
        website: values.website || null,
        email: values.email || null,
        iban: values.iban || null,
        latitude: values.latitude,
        longitude: values.longitude,
        status: values.address_status,
      })
    }
    toast.success(t('congregations.edit.address.saveSuccess', 'Adres został zapisany'))
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
    await loadCongregation()
  } catch (error) {
    logSafeError('Failed to save address:', error)
    handleError(error, { setErrors: form.setErrors, fallbackMessage: t('congregations.edit.address.saveError', 'Nie udało się zapisać adresu') })
  }
})

async function saveServiceTimes() {
  try {
    // Remove service times the user deleted from the form
    for (const id of deletedServiceTimeIds.value) {
      await congregationApiService.deleteServiceTime(congregationId, id)
    }

    // Update existing service times, create newly added ones
    for (const st of serviceTimeFields.value) {
      const payload = { day: st.day, time: st.time, description: st.description || null, order: st.order }
      if (st.id) {
        await congregationApiService.updateServiceTime(congregationId, st.id, payload)
      } else {
        await congregationApiService.createServiceTime(congregationId, payload)
      }
    }

    deletedServiceTimeIds.value = []
    toast.success(t('congregations.edit.serviceTimes.saveSuccess', 'Godziny nabożeństw zostały zapisane'))
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
    await loadCongregation()
  } catch (error) {
    logSafeError('Failed to save service times:', error)
    handleError(error, { fallbackMessage: t('congregations.edit.serviceTimes.saveError', 'Nie udało się zapisać godzin nabożeństw') })
  }
}

function addServiceTime() {
  pushServiceTime({ day: '', time: '', description: '', order: serviceTimeFields.value.length })
}

function removeServiceTimeAt(index: number) {
  removeServiceTime(index)
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

      <p
        v-if="congregationFull?.address?.last_updated_label"
        class="max-w-4xl mx-auto text-xs text-muted-foreground"
      >
        {{ t('congregations.edit.lastUpdatedBy', 'Ostatnia zmiana danych') }}:
        {{ congregationFull.address.last_updated_label }}
        <span v-if="congregationFull.address.last_updated_at">
          · {{ new Date(congregationFull.address.last_updated_at).toLocaleString() }}
        </span>
      </p>

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

            <div class="grid grid-cols-2 gap-4">
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

            <div class="grid grid-cols-2 gap-4">
              <FormField v-slot="{ componentField }" name="country">
                <FormItem>
                  <FormLabel>
                    {{ t('congregations.edit.address.country', 'Kraj') }}
                  </FormLabel>
                  <Select v-bind="componentField">
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem
                        v-for="option in countries"
                        :key="option.code"
                        :value="option.code"
                      >
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              </FormField>

              <FormField v-slot="{ componentField }" name="province">
                <FormItem>
                  <FormLabel>
                    {{ t('congregations.edit.address.province', 'Województwo') }}
                  </FormLabel>
                  <Select v-bind="componentField" :disabled="provinces.length === 0">
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue
                          :placeholder="t('congregations.edit.address.provincePlaceholder', 'Wybierz województwo')"
                        />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem
                        v-for="option in provinces"
                        :key="option"
                        :value="option"
                      >
                        {{ provinceLabel(option) }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              </FormField>
            </div>

            <FormField v-slot="{ componentField }" name="website">
              <FormItem>
                <FormLabel>
                  {{ t('congregations.edit.address.website', 'Strona WWW') }}
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    :placeholder="t('congregations.edit.address.websitePlaceholder', 'np. https://example.pl')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField v-slot="{ componentField }" name="email">
                <FormItem>
                  <FormLabel>
                    {{ t('congregations.edit.address.email', 'E-mail zboru') }}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      :placeholder="t('congregations.edit.address.emailPlaceholder', 'np. kontakt@example.pl')"
                      v-bind="componentField"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>

              <FormField v-slot="{ componentField }" name="iban">
                <FormItem>
                  <FormLabel>
                    {{ t('congregations.edit.address.iban', 'Numer konta') }}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      :placeholder="t('congregations.edit.address.ibanPlaceholder', 'np. 61 1090 1014 0000 0712 1981 2874')"
                      v-bind="componentField"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <Label>
                  {{ t('congregations.edit.address.location') }}
                </Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  :disabled="!form.values.city || geocoding"
                  @click="geocodeAddress"
                >
                  {{ geocoding ? t('congregations.edit.address.geocoding') : t('congregations.edit.address.geocodeButton') }}
                </Button>
              </div>
              <AddressMapPicker v-model:latitude="latitudeModel" v-model:longitude="longitudeModel" />
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <Label>{{ t('congregations.edit.address.latitude') }}</Label>
                  <Input
                    v-model.number="latitudeInputModel"
                    type="number"
                    step="any"
                    min="-90"
                    max="90"
                  />
                </div>
                <div>
                  <Label>{{ t('congregations.edit.address.longitude') }}</Label>
                  <Input
                    v-model.number="longitudeInputModel"
                    type="number"
                    step="any"
                    min="-180"
                    max="180"
                  />
                </div>
              </div>
            </div>

            <FormField v-slot="{ componentField }" name="address_status">
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
                <div class="flex-1 space-y-4">
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <Label>
                        {{ t('congregations.edit.serviceTime.day', 'Dzień') }}
                      </Label>
                      <Input
                        v-model="field.day"
                        :placeholder="t('congregations.edit.serviceTime.dayPlaceholder', 'np. Niedziela')"
                      />
                    </div>

                    <div>
                      <Label>
                        {{ t('congregations.edit.serviceTime.time', 'Godzina') }}
                      </Label>
                      <Input
                        v-model="field.time"
                        type="time"
                        :placeholder="t('congregations.edit.serviceTime.timePlaceholder', 'np. 10:00')"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>
                      {{ t('congregations.edit.serviceTime.description', 'Opis') }}
                    </Label>
                    <Input
                      v-model="field.description"
                      maxlength="256"
                      :placeholder="t('congregations.edit.serviceTime.descriptionPlaceholder', 'np. Modlitwa nocna')"
                    />
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="shrink-0 self-center"
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

        <ChurchPeopleSection :church-id="congregationId" />
        <ChurchBranchesSection :church-id="congregationId" />
        <ShareLinksSection :tenant-id="congregationId" />
        <ChangeHistorySection :tenant-id="congregationId" />
      </div>
    </div>
  </AuthenticatedLayout>
</template>
