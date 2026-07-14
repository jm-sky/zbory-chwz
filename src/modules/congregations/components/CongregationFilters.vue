<script setup lang="ts">
import { ChevronDown, ChevronUp, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import { Checkbox } from '@/components/ui/checkbox'
import SearchInput from '@/components/ui/input/SearchInput.vue'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { CongregationListViewMode } from '../types/congregationListView.types'
import { ANY_VALUE } from '../composables/useCongregationFilters'
import { countryLabel, provinceLabel } from '../utils/geo'
import CongregationViewModeToggle from './CongregationViewModeToggle.vue'

const { locale, t } = useI18n()

const { availableCountries, availableProvinces, hasBranches, isFiltered, resultCount } = defineProps<{
  availableCountries: string[]
  availableProvinces: string[]
  hasBranches: boolean
  isFiltered: boolean
  resultCount: number
}>()

const search = defineModel<string>('search', { required: true })
const country = defineModel<string>('country', { required: true })
const province = defineModel<string>('province', { required: true })
const hideBranches = defineModel<boolean>('hideBranches', { required: true })
const viewMode = defineModel<CongregationListViewMode>('viewMode', { required: true })

const emit = defineEmits<{ reset: [] }>()

const showAdvancedFilters = ref(false)

const countryItems = computed<Array<{ value: string; label: string }>>(() =>
  availableCountries.map((code) => ({ value: code, label: countryLabel(code, locale.value) })),
)

const provinceItems = computed<Array<{ value: string; label: string }>>(() =>
  availableProvinces.map((slug) => ({ value: slug, label: provinceLabel(slug) })),
)

const hasActiveGeoFilters = computed<boolean>(() =>
  country.value !== ANY_VALUE || province.value !== ANY_VALUE,
)

onMounted(() => {
  if (hasActiveGeoFilters.value) {
    showAdvancedFilters.value = true
  }
})

function toggleAdvancedFilters(): void {
  showAdvancedFilters.value = !showAdvancedFilters.value
}
</script>

<template>
  <div class="space-y-3 rounded-lg border bg-card p-4">
    <div class="flex items-center gap-2">
      <SearchInput
        id="congregations-search"
        v-model="search"
        name="congregations-search"
        :placeholder="t('congregations.filters.searchPlaceholder')"
      />

      <Button
        variant="ghost"
        size="sm"
        class="h-8 shrink-0 px-2 text-muted-foreground"
        :aria-label="showAdvancedFilters ? t('congregations.filters.less') : t('congregations.filters.more')"
        :aria-expanded="showAdvancedFilters"
        @click="toggleAdvancedFilters"
      >
        <ChevronUp v-if="showAdvancedFilters" class="size-4" />
        <ChevronDown v-else class="size-4" />
        <span class="hidden sm:inline">
          {{ showAdvancedFilters ? t('congregations.filters.less') : t('congregations.filters.more') }}
        </span>
      </Button>
    </div>

    <div v-show="showAdvancedFilters" class="grid gap-3 sm:grid-cols-2">
      <div class="space-y-1.5">
        <Label for="congregations-country">
          {{ t('congregations.filters.country') }}
        </Label>
        <Select v-model="country">
          <SelectTrigger id="congregations-country" class="w-full">
            <SelectValue :placeholder="t('congregations.filters.anyCountry')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem :value="ANY_VALUE">
              {{ t('congregations.filters.anyCountry') }}
            </SelectItem>
            <SelectItem
              v-for="item in countryItems"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div class="space-y-1.5">
        <Label for="congregations-province">
          {{ t('congregations.filters.province') }}
        </Label>
        <Select v-model="province" :disabled="provinceItems.length === 0">
          <SelectTrigger id="congregations-province" class="w-full">
            <SelectValue :placeholder="t('congregations.filters.anyProvince')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem :value="ANY_VALUE">
              {{ t('congregations.filters.anyProvince') }}
            </SelectItem>
            <SelectItem
              v-for="item in provinceItems"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <div class="flex items-end justify-between gap-3">
      <div v-if="hasBranches" class="flex items-center gap-2">
        <Checkbox id="congregations-hide-branches" v-model="hideBranches" />
        <Label for="congregations-hide-branches" class="cursor-pointer font-normal">
          {{ t('congregations.filters.hideBranches') }}
        </Label>
      </div>
      <span v-else />

      <div class="flex items-center gap-2">
        <CongregationViewModeToggle v-model:view-mode="viewMode" />
        <Button
          v-if="isFiltered"
          variant="ghost"
          size="sm"
          @click="emit('reset')"
        >
          <X class="size-4" />
          {{ t('congregations.filters.reset') }}
        </Button>
      </div>
    </div>

    <p class="text-sm text-muted-foreground">
      {{ t('congregations.filters.resultCount', { count: resultCount }, resultCount) }}
    </p>
  </div>
</template>
