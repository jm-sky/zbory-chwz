<script setup lang="ts">
import { computed } from 'vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface DiffFieldState {
  field: string
  label: string
  group: string
  oldValue: string | null
  newValue: string
  apply: boolean
}

const { fields, group } = defineProps<{
  fields: DiffFieldState[]
  group: string
}>()

const groupFields = computed(() => fields.filter(field => field.group === group))
</script>

<template>
  <div v-if="groupFields.length > 0" class="space-y-3">
    <h4 class="text-sm font-semibold">
      <slot />
    </h4>
    <div v-for="field in groupFields" :key="field.field" class="flex items-center gap-3">
      <Checkbox v-model="field.apply" />
      <div class="flex-1 space-y-1">
        <Label class="text-xs text-muted-foreground">{{ field.label }}</Label>
        <div class="flex items-center gap-2 flex-wrap">
          <span v-if="field.oldValue" class="text-sm text-muted-foreground line-through">
            {{ field.oldValue }}
          </span>
          <Input v-model="field.newValue" class="max-w-xs" />
        </div>
      </div>
    </div>
  </div>
</template>
