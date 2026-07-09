<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Input } from '@/components/ui/input'
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
import { getVisibilityIcon } from '../utils/visibility'

const modelValue = defineModel<string>({ required: true })
const visibility = defineModel<VisibilityLevel>('visibility', { required: true })

const { readonly = false, disabled = false } = defineProps<{
  readonly?: boolean
  disabled?: boolean
  type?: string
}>()

const { t } = useI18n()

function visibilityLabel(level: VisibilityLevel): string {
  return t(`congregations.people.visibility.${level}`)
}
</script>

<template>
  <div class="flex max-w-md">
    <Input
      v-model="modelValue"
      :type="type"
      :readonly="readonly"
      :disabled="disabled"
      class="min-w-0 flex-1 rounded-r-none focus-visible:z-10"
    />
    <Select
      v-model="visibility"
      :disabled="disabled"
    >
      <SelectTrigger
        class="w-auto shrink-0 gap-1 rounded-l-none border-l-0 px-2"
        :aria-label="visibilityLabel(visibility)"
      >
        <SelectValue>
          <template #default="{ modelValue: selectedLevel }">
            <component
              :is="getVisibilityIcon((selectedLevel ?? visibility) as VisibilityLevel)"
              class="size-4 shrink-0"
            />
          </template>
        </SelectValue>
      </SelectTrigger>
      <SelectContent class="z-[100]">
        <SelectItem
          v-for="level in VISIBILITY_LEVELS"
          :key="level"
          :value="level"
        >
          <span class="flex items-center gap-2">
            <component
              :is="getVisibilityIcon(level)"
              class="size-4 shrink-0 text-muted-foreground"
            />
            {{ visibilityLabel(level) }}
          </span>
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>
