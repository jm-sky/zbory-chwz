<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

// Local type definition (removed gear module dependency)
type TShelfLifeUnit = 'days' | 'months' | 'years'

interface Emits {
  (e: 'update:modelValue', value: number | undefined): void
  (e: 'update:unit', value: TShelfLifeUnit): void
}

const props = withDefaults(defineProps<{
  modelValue?: number
  unit?: TShelfLifeUnit
  placeholder?: string
  disabled?: boolean
}>(), {
  placeholder: '',
  disabled: false,
  unit: 'years',
})

const emit = defineEmits<Emits>()

const { t } = useI18n()

const shelfLifeUnits: TShelfLifeUnit[] = ['days', 'months', 'years']

const handleValueInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const value = target.value === '' ? undefined : Number.parseInt(target.value, 10)
  emit('update:modelValue', value)
}

const handleUnitChange = (value: unknown) => {
  if (typeof value === 'string') {
    emit('update:unit', value as TShelfLifeUnit)
  }
}

const currentValue = computed<number | undefined>(() => props.modelValue)
const currentUnit = computed<TShelfLifeUnit | undefined>(() => props.unit)
</script>

<template>
  <div class="grid grid-cols-[1fr_120px] sm:grid-cols-[1fr_auto] gap-2">
    <Input
      :model-value="currentValue"
      :placeholder="placeholder"
      :disabled="disabled"
      type="number"
      min="1"
      step="1"
      @input="handleValueInput"
    />
    <Select :model-value="currentUnit" @update:model-value="handleUnitChange">
      <SelectTrigger class="w-[120px] sm:w-auto">
        <SelectValue :placeholder="t('gear.item.shelfLifeUnitPlaceholder')" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem
          v-for="unitOption in shelfLifeUnits"
          :key="unitOption"
          :value="unitOption"
        >
          {{ t(`gear.item.shelfLifeUnit.${unitOption}`) }}
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>

