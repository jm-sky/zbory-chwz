<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import {
  VISIBILITY_LEVELS,
  type VisibilityLevel,
} from '../types/visibility.types'
import { getVisibilityIcon } from '../utils/visibility'
import type { HTMLAttributes } from 'vue'

const visibility = defineModel<VisibilityLevel>({ required: true })

const { disabled = false, triggerClass } = defineProps<{
  disabled?: boolean
  triggerClass?: HTMLAttributes['class']
}>()

const { t } = useI18n()

function visibilityLabel(level: VisibilityLevel): string {
  return t(`congregations.people.visibility.${level}`)
}
</script>

<template>
  <Select v-model="visibility" :disabled="disabled">
    <Tooltip>
      <TooltipTrigger as-child>
        <SelectTrigger
          :class="cn('size-9 shrink-0 justify-center gap-0 px-0 [&>span[aria-hidden=true]]:hidden', triggerClass)"
          :aria-label="visibilityLabel(visibility)"
        >
          <component
            :is="getVisibilityIcon(visibility)"
            class="size-4 shrink-0 pointer-events-none"
          />
          <SelectValue class="sr-only">
            {{ visibilityLabel(visibility) }}
          </SelectValue>
        </SelectTrigger>
      </TooltipTrigger>
      <TooltipContent>
        {{ visibilityLabel(visibility) }}
      </TooltipContent>
    </Tooltip>
    <SelectContent class="z-[100]">
      <SelectItem
        v-for="level in VISIBILITY_LEVELS"
        :key="level"
        :value="level"
        :text-value="visibilityLabel(level)"
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
</template>
