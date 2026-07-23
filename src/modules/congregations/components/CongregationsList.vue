<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { Church, Plus, Search } from 'lucide-vue-next'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import Button from '@/components/ui/button/Button.vue'
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
import { Textarea } from '@/components/ui/textarea'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { useHandleError } from '@/shared/composables/useHandleError'
import { logSafeError } from '@/shared/utils/logSafeError'
import type { ICongregationDetailed } from '../types/congregation.types'
import { useCongregationFilters } from '../composables/useCongregationFilters'
import { useCongregationFiltersUrl } from '../composables/useCongregationFiltersUrl'
import { useCongregationListViewMode } from '../composables/useCongregationListViewMode'
import { useCongregations } from '../composables/useCongregations'
import { CongregationRoutePaths } from '../routes'
import { congregationApiService } from '../services/congregationApiService'
import { congregationKeys } from '../utils/congregationKeys'
import CongregationExportMenu from './CongregationExportMenu.vue'
import CongregationFilters from './CongregationFilters.vue'
import CongregationListCard from './CongregationListCard.vue'
import CongregationListRow from './CongregationListRow.vue'
import CongregationsMapView from './map/CongregationsMapView.vue'

const { t } = useI18n()
const route = useRoute()
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
const { viewMode } = useCongregationListViewMode()

const {
  search,
  country,
  province,
  hideBranches,
  userLocation,
  maxDistanceKm,
  sortByDistance,
  availableCountries,
  availableProvinces,
  hasBranches,
  isFiltered,
  filtered: filteredCongregations,
  missingCoordinatesCount,
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

async function handleEdit(congregation: ICongregationDetailed) {
  router.push(CongregationRoutePaths.editById(congregation.id))
}

function handleOpen(congregation: ICongregationDetailed) {
  if (congregation.type === 'branch') return
  router.push({ path: CongregationRoutePaths.detailById(congregation.id), query: route.query })
}

function handleMapMarkerOpen(id: string): void {
  const congregation = filteredCongregations.value.find(c => c.id === id)
  if (congregation) handleOpen(congregation)
}

async function handleUnpublish(congregation: ICongregationDetailed) {
  if (!confirm(t('congregations.list.unpublishConfirm', 'Czy na pewno chcesz cofnąć publikację tego zboru?'))) {
    return
  }

  try {
    await congregationApiService.unpublishCongregation(congregation.id)
    toast.success(t('congregations.list.unpublishSuccess', 'Zbór został cofnięty z publikacji'))
    // Invalidate and refetch congregations
    await queryClient.invalidateQueries({ queryKey: congregationKeys.all, refetchType: 'all' })
  } catch (error) {
    logSafeError('Failed to unpublish congregation:', error)
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
    toast.info(t('congregations.list.createDraftHint', 'Zbór jest widoczny jako szkic. Aby opublikować go publicznie, uzupełnij adres i ustaw status adresu na opublikowany.'))
    createDialogOpen.value = false
    resetCreateForm()
    await queryClient.invalidateQueries({ queryKey: congregationKeys.all, refetchType: 'all' })
    // A congregation only appears on this public list once it has a published
    // address — send the admin straight to the edit page to fill it in.
    router.push(CongregationRoutePaths.editById(created.id))
  } catch (error) {
    logSafeError('Failed to create congregation:', error)
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
    await queryClient.invalidateQueries({ queryKey: congregationKeys.all, refetchType: 'all' })
  } catch (error) {
    logSafeError('Failed to delete congregation:', error)
    handleError(error, { fallbackMessage: t('congregations.list.deleteError', 'Nie udało się usunąć zboru') })
  }
}
</script>

<template>
  <div class="space-y-6">
    <CommonPageHeader
      :icon="Church"
      :label="t('congregations.list.title', 'Zbory CHWZ')"
      :description="t('congregations.list.description', 'Lista zborów Chrześcijańskiej Wspólnoty Zielonoświątkowej')"
    >
      <template #actions>
        <Button
          v-if="canCreateOrDelete()"
          v-tooltip="t('congregations.list.create', 'Dodaj zbór')"
          size="sm"
          :aria-label="t('congregations.list.create', 'Dodaj zbór')"
          @click="createDialogOpen = true"
        >
          <Plus class="size-4" />
          <span class="hidden sm:inline">
            {{ t('congregations.list.create', 'Dodaj zbór') }}
          </span>
        </Button>
        <CongregationExportMenu
          v-if="!isLoading && !error && congregations && congregations.length > 0"
          :congregations="filteredCongregations"
        />
      </template>
    </CommonPageHeader>

    <div class="space-y-4">
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
          v-model:view-mode="viewMode"
          v-model:max-distance-km="maxDistanceKm"
          v-model:sort-by-distance="sortByDistance"
          v-model:user-location="userLocation"
          :available-countries="availableCountries"
          :available-provinces="availableProvinces"
          :has-branches="hasBranches"
          :is-filtered="isFiltered"
          :result-count="filteredCongregations.length"
          :missing-coordinates-count="missingCoordinatesCount"
          @reset="reset"
        />
      </template>

      <!-- Loading State -->
      <div v-if="isLoading" class="space-y-3">
        <div
          v-for="i in 5"
          :key="i"
          :class="viewMode === 'grid' ? 'h-32 animate-pulse rounded-lg bg-muted' : 'h-16 animate-pulse rounded-lg bg-muted'"
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

      <!-- Congregations Map -->
      <CongregationsMapView
        v-else-if="viewMode === 'map'"
        :congregations="filteredCongregations"
        :user-location="userLocation"
        @open="handleMapMarkerOpen"
      />

      <!-- Congregations Grid -->
      <div v-else-if="viewMode === 'grid'" class="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
        <CongregationListCard
          v-for="congregation in filteredCongregations"
          :key="congregation.id"
          :congregation="congregation"
          :can-manage="canManageCongregation(congregation)"
          :can-delete="canCreateOrDelete()"
          :show-completeness="canCreateOrDelete()"
          @open="handleOpen(congregation)"
          @edit="handleEdit(congregation)"
          @unpublish="handleUnpublish(congregation)"
          @delete="handleDelete(congregation)"
        />
      </div>

      <!-- Congregations List -->
      <div v-else class="divide-y rounded-lg border">
        <CongregationListRow
          v-for="congregation in filteredCongregations"
          :key="congregation.id"
          :congregation="congregation"
          :can-manage="canManageCongregation(congregation)"
          :can-delete="canCreateOrDelete()"
          :show-completeness="canCreateOrDelete()"
          @open="handleOpen(congregation)"
          @edit="handleEdit(congregation)"
          @unpublish="handleUnpublish(congregation)"
          @delete="handleDelete(congregation)"
        />
      </div>
    </div>
  </div>
</template>
