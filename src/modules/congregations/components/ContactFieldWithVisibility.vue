<script setup lang="ts">
import { Input } from '@/components/ui/input'
import type { VisibilityLevel } from '../types/visibility.types'
import VisibilityLevelIconSelect from './VisibilityLevelIconSelect.vue'

defineOptions({ inheritAttrs: false })

const modelValue = defineModel<string>({ required: true })
const visibility = defineModel<VisibilityLevel>('visibility', { required: true })

const { readonly = false, disabled = false } = defineProps<{
  readonly?: boolean
  disabled?: boolean
  type?: string
}>()
</script>

<template>
  <div class="flex max-w-md">
    <Input
      v-model="modelValue"
      v-bind="$attrs"
      :type="type"
      :readonly="readonly"
      :disabled="disabled"
      class="min-w-0 flex-1 rounded-r-none focus-visible:z-10"
    />
    <VisibilityLevelIconSelect
      v-model="visibility"
      :disabled="disabled"
      trigger-class="rounded-l-none border-l-0"
    />
  </div>
</template>
