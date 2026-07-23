<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { config } from '@/shared/config/config'

// Local type definition (removed gear module dependency)
type TGearWeightUnit = 'g' | 'kg' | 'oz' | 'lb'

interface Emits {
  (e: 'update:modelValue', value: number | undefined): void
  (e: 'update:unit', value: TGearWeightUnit): void
}

const props = withDefaults(defineProps<{
  modelValue?: number
  unit?: TGearWeightUnit
  placeholder?: string
  required?: boolean
  disabled?: boolean
  min?: number
  step?: number
}>(), {
  placeholder: '',
  required: false,
  disabled: false,
  min: 0,
  step: 0.01,
  unit: config.defaults.preferredWeightUnit,
})

const emit = defineEmits<Emits>()

const { t } = useI18n()

const handleWeightInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const value = target.value === '' ? undefined : Number.parseFloat(target.value)
  emit('update:modelValue', value)
}

const handleUnitChange = (value: unknown) => {
  if (typeof value === 'string') {
    emit('update:unit', value as TGearWeightUnit)
  }
}

const currentWeight = computed(() => props.modelValue)
const currentUnit = computed(() => props.unit ?? config.defaults.preferredWeightUnit)
</script>

<template>
  <div class="grid grid-cols-[1fr_80px] sm:grid-cols-[1fr_auto] gap-2">
    <Input
      :model-value="currentWeight"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :min="min"
      :step="step"
      type="number"
      @input="handleWeightInput"
    />
    <Select :model-value="currentUnit" @update:model-value="handleUnitChange">
      <SelectTrigger class="w-[80px] sm:w-auto">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="g">
          {{ t('gear.item.weightUnits.g') }}
        </SelectItem>
        <SelectItem value="kg">
          {{ t('gear.item.weightUnits.kg') }}
        </SelectItem>
        <SelectItem value="oz">
          {{ t('gear.item.weightUnits.oz') }}
        </SelectItem>
        <SelectItem value="lb">
          {{ t('gear.item.weightUnits.lb') }}
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>

