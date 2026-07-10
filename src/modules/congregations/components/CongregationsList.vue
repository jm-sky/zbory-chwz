<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Church, Clock, Edit, EyeOff, Mail, MapPin, MoreHorizontal, Phone, Plus, Search, Trash2, User } from 'lucide-vue-next'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { ICongregationDetailed } from '../types/congregation.types'
import { useCongregationFilters } from '../composables/useCongregationFilters'
import { useCongregationFiltersUrl } from '../composables/useCongregationFiltersUrl'
import { useCongregations } from '../composables/useCongregations'
import { CongregationRoutePaths } from '../routes'
import { congregationApiService } from '../services/congregationApiService'
import { contactsOf } from '../utils/exportCongregations'
import CongregationExportMenu from './CongregationExportMenu.vue'
import CongregationFilters from './CongregationFilters.vue'

const { t } = useI18n()
const router = useRouter()
const queryClient = useQueryClient()
const authStore = useAuthStore()
const { handleError } = useHandleError()
const { data: congregations, isLoading, error } = useCongregations()

// Only global admins/owners can create or hard-manage congregations;
// tenant-scoped "role" only allows editing/unpublishing their own congregation.
const canCreateOrDelete = () => !!(authStore.user?.isAdmin || authStore.user?.isOwner)

const createDialogOpen = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

function resetCreateForm() {
  createForm.value = { name: '', description: '' }
}

const congregationFilters = useCongregationFilters(congregations)
useCongregationFiltersUrl(congregationFilters)

const {
  search,
  country,
  province,
  hideBranches,
  availableCountries,
  availableProvinces,
  hasBranches,
  isFiltered,
  filtered: filteredCongregations,
  reset,
} = congregationFilters

// Check if user can edit/unpublish a congregation
function canManageCongregation(congregation: ICongregationDetailed): boolean {
  // Branches are edited from their parent congregation, not from this list
  if (congregation.type === 'branch') {
    return false
  }
  // Admin or owner can manage any congregation
  if (authStore.user?.isAdmin || authStore.user?.isOwner) {
    return true
  }
  // Tenant user (has role for this congregation)
  return !!congregation.role
}

function formatAddress(congregation: ICongregationDetailed): string {
  const parts: string[] = []
  if (congregation.street) parts.push(congregation.street)
  if (congregation.postal_code && congregation.city) {
    parts.push(`${congregation.postal_code} ${congregation.city}`)
  } else if (congregation.city) {
    parts.push(congregation.city)
  }
  return parts.join(', ') || ''
}

function formatServiceTimes(serviceTimes?: Array<{ day: string; time: string }>): string {
  if (!serviceTimes || serviceTimes.length === 0) return ''
  return serviceTimes.map((st) => `${st.day} ${st.time}`).join(', ')
}

async function handleEdit(congregation: ICongregationDetailed) {
  router.push(CongregationRoutePaths.editById(congregation.id))
}

async function handleUnpublish(congregation: ICongregationDetailed) {
  if (!confirm(t('congregations.list.unpublishConfirm', 'Czy na pewno chcesz cofnąć publikację tego zboru?'))) {
    return
  }

  try {
    await congregationApiService.unpublishCongregation(congregation.id)
    toast.success(t('congregations.list.unpublishSuccess', 'Zbór został cofnięty z publikacji'))
    // Invalidate and refetch congregations
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
  } catch (error) {
    console.error('Failed to unpublish congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.list.unpublishError', 'Nie udało się cofnąć publikacji zboru') })
  }
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    toast.error(t('congregations.list.nameRequired', 'Nazwa jest wymagana'))
    return
  }

  creating.value = true
  try {
    const created = await congregationApiService.createCongregation({
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim() || undefined,
    })
    toast.success(t('congregations.list.createSuccess', 'Zbór został utworzony'))
    createDialogOpen.value = false
    resetCreateForm()
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
    // A congregation only appears on this public list once it has a published
    // address — send the admin straight to the edit page to fill it in.
    router.push(CongregationRoutePaths.editById(created.id))
  } catch (error) {
    console.error('Failed to create congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.list.createError', 'Nie udało się utworzyć zboru') })
  } finally {
    creating.value = false
  }
}

async function handleDelete(congregation: ICongregationDetailed) {
  if (!confirm(t('congregations.list.deleteConfirm', 'Czy na pewno chcesz usunąć ten zbór?'))) {
    return
  }

  try {
    await congregationApiService.deleteCongregation(congregation.id)
    toast.success(t('congregations.list.deleteSuccess', 'Zbór został usunięty'))
    await queryClient.invalidateQueries({ queryKey: ['congregations'] })
  } catch (error) {
    console.error('Failed to delete congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.list.deleteError', 'Nie udało się usunąć zboru') })
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Create + export -->
    <div v-if="canCreateOrDelete() || (!isLoading && !error && congregations && congregations.length > 0)" class="flex justify-end gap-2">
      <Button v-if="canCreateOrDelete()" size="sm" @click="createDialogOpen = true">
        <Plus class="size-4" />
        {{ t('congregations.list.create', 'Dodaj zbór') }}
      </Button>
      <CongregationExportMenu
        v-if="!isLoading && !error && congregations && congregations.length > 0"
        :congregations="filteredCongregations"
      />
    </div>

    <Dialog v-model:open="createDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {{ t('congregations.list.createTitle', 'Dodaj nowy zbór') }}
          </DialogTitle>
          <DialogDescription>
            {{ t('congregations.list.createDescription', 'Utwórz nowy zbór. Pełne dane (adres, godziny nabożeństw) uzupełnisz po utworzeniu.') }}
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-4">
          <div class="space-y-2">
            <Label for="create-congregation-name">
              {{ t('congregations.edit.basicInfo.name', 'Nazwa') }} *
            </Label>
            <Input
              id="create-congregation-name"
              v-model="createForm.name"
              :placeholder="t('congregations.edit.basicInfo.namePlaceholder', 'Wprowadź nazwę zboru')"
            />
          </div>
          <div class="space-y-2">
            <Label for="create-congregation-description">
              {{ t('congregations.edit.basicInfo.description', 'Opis') }}
            </Label>
            <Textarea
              id="create-congregation-description"
              v-model="createForm.description"
              :placeholder="t('congregations.edit.basicInfo.descriptionPlaceholder', 'Wprowadź opis zboru (opcjonalnie)')"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="createDialogOpen = false">
            {{ t('common.cancel', 'Anuluj') }}
          </Button>
          <Button :disabled="creating" @click="handleCreate">
            {{ t('common.create', 'Utwórz') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Filters -->
    <template v-if="!isLoading && !error && congregations && congregations.length > 0">
      <CongregationFilters
        v-model:search="search"
        v-model:country="country"
        v-model:province="province"
        v-model:hide-branches="hideBranches"
        :available-countries="availableCountries"
        :available-provinces="availableProvinces"
        :has-branches="hasBranches"
        :is-filtered="isFiltered"
        :result-count="filteredCongregations.length"
        @reset="reset"
      />
    </template>

    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-3">
      <div
        v-for="i in 5"
        :key="i"
        class="h-32 animate-pulse rounded-lg bg-muted"
      />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center text-sm text-destructive">
      {{ t('congregations.list.error', 'Nie udało się załadować listy zborów') }}
    </div>

    <!-- Empty State -->
    <div v-else-if="!congregations || congregations.length === 0" class="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
      <Church class="mx-auto mb-2 size-8 opacity-50" />
      <p>{{ t('congregations.list.empty', 'Brak zborów do wyświetlenia') }}</p>
    </div>

    <!-- No Search Results -->
    <div v-else-if="filteredCongregations.length === 0" class="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
      <Search class="mx-auto mb-2 size-8 opacity-50" />
      <p>{{ t('congregations.list.noResults', 'Brak wyników dla podanej frazy') }}</p>
    </div>

    <!-- Congregations List -->
    <div v-else class="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
      <div
        v-for="congregation in filteredCongregations"
        :key="congregation.id"
        :class="[
          'group rounded-lg border p-6 transition-all hover:shadow-md',
          congregation.status === 'published_unverified'
            ? 'bg-muted/30 border-muted-foreground/20 hover:border-muted-foreground/40 opacity-90'
            : 'bg-card hover:border-primary/50'
        ]"
      >
        <!-- Header -->
        <div class="mb-4 flex items-start gap-4">
          <div class="flex size-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
            <Church class="size-6 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <h3
                :class="[
                  'text-lg font-semibold leading-tight',
                  congregation.status === 'published_unverified' ? 'text-muted-foreground' : 'text-foreground'
                ]"
              >
                {{ congregation.name }}
              </h3>
              <Badge v-if="congregation.type === 'branch'" variant="secondary">
                {{ t('congregations.list.branch') }}
              </Badge>
              <Badge
                v-if="congregation.status === 'published_unverified'"
                variant="outline"
                class="opacity-60 text-muted-foreground border-muted-foreground/50"
              >
                {{ t('congregations.status.unverified', 'Draft') }}
              </Badge>
            </div>
            <p
              v-if="congregation.type === 'branch' && congregation.parent_name"
              class="mt-1 text-sm text-muted-foreground"
            >
              {{ t('congregations.list.branchOf', { name: congregation.parent_name }) }}
            </p>
            <p
              v-if="congregation.description"
              :class="[
                'mt-1 text-sm line-clamp-2',
                congregation.status === 'published_unverified' ? 'text-muted-foreground/70' : 'text-muted-foreground'
              ]"
            >
              {{ congregation.description }}
            </p>
          </div>
          <!-- Actions Dropdown -->
          <DropdownMenu v-if="canManageCongregation(congregation)">
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="shrink-0">
                <MoreHorizontal class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="handleEdit(congregation)">
                <Edit class="size-4" />
                <span>{{ t('common.edit', 'Edytuj') }}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                v-if="congregation.status === 'published' || congregation.status === 'published_unverified'"
                @click="handleUnpublish(congregation)"
              >
                <EyeOff class="size-4" />
                <span>{{ t('congregations.list.unpublish', 'Cofnij publikację') }}</span>
              </DropdownMenuItem>
              <template v-if="canCreateOrDelete()">
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  class="text-destructive focus:text-destructive"
                  @click="handleDelete(congregation)"
                >
                  <Trash2 class="size-4" />
                  <span>{{ t('common.delete', 'Usuń') }}</span>
                </DropdownMenuItem>
              </template>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <!-- Details Grid -->
        <div class="space-y-3">
          <!-- Address -->
          <div v-if="formatAddress(congregation)" class="flex items-start gap-2 text-sm">
            <MapPin class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="text-muted-foreground">{{ formatAddress(congregation) }}</span>
          </div>

          <!-- Service Times -->
          <div v-if="formatServiceTimes(congregation.service_times)" class="flex items-start gap-2 text-sm">
            <Clock class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="text-muted-foreground">{{ formatServiceTimes(congregation.service_times) }}</span>
          </div>

          <!-- Card contacts -->
          <div
            v-for="(contact, contactIndex) in contactsOf(congregation)"
            :key="`${congregation.id}-contact-${contactIndex}`"
            class="space-y-1.5"
          >
            <div class="flex items-start gap-2 text-sm">
              <User class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div class="min-w-0 flex-1">
                <span class="font-medium text-foreground">{{ contact.name }}</span>
                <span v-if="contact.title" class="text-muted-foreground">
                  {{ ` - ${contact.title}` }}
                </span>
              </div>
            </div>
            <div
              v-if="contact.phone || contact.email"
              class="ml-6 space-y-1.5 text-sm"
            >
              <a
                v-if="contact.phone"
                :href="`tel:${contact.phone}`"
                class="flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <Phone class="size-3.5" />
                <span>{{ contact.phone }}</span>
              </a>
              <a
                v-if="contact.email"
                :href="`mailto:${contact.email}`"
                class="flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <Mail class="size-3.5" />
                <span class="break-all">{{ contact.email }}</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
