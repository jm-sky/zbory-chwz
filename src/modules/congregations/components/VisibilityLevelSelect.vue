<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  VISIBILITY_LEVELS,
  type VisibilityLevel,
} from '../types/visibility.types'

const modelValue = defineModel<VisibilityLevel>({ required: true })

const { label, disabled = false, levels = VISIBILITY_LEVELS } = defineProps<{
  label: string
  disabled?: boolean
  levels?: VisibilityLevel[]
}>()

const { t } = useI18n()

function visibilityLabel(level: VisibilityLevel): string {
  return t(`congregations.people.visibility.${level}`)
}
</script>

<template>
  <div class="space-y-1">
    <Label>{{ label }}</Label>
    <Select
      v-model="modelValue"
      :disabled="disabled"
    >
      <SelectTrigger class="max-w-md">
        <SelectValue />
      </SelectTrigger>
      <SelectContent class="z-[100]">
        <SelectItem
          v-for="level in levels"
          :key="level"
          :value="level"
        >
          {{ visibilityLabel(level) }}
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>
