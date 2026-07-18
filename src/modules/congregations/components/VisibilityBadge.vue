<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import type { VisibilityLevel } from '../types/visibility.types'
import { getVisibilityIcon } from '../utils/visibility'
import type { BadgeVariants } from '@/components/ui/badge'

const { level, compact = false } = defineProps<{
  level: VisibilityLevel
  /** Icon-only, wrapped in a tooltip showing the label — for tight spaces like next to a phone/email link. */
  compact?: boolean
}>()

const { t } = useI18n()

const VARIANT_BY_LEVEL: Record<VisibilityLevel, NonNullable<BadgeVariants['variant']>> = {
  hidden: 'destructive-outline',
  public: 'success-outline',
  authenticated: 'outline',
  pastors: 'primary-outline',
}

const label = computed<string>(() => t(`congregations.people.visibility.${level}`))
const icon = computed(() => getVisibilityIcon(level))
const variant = computed<NonNullable<BadgeVariants['variant']>>(() => VARIANT_BY_LEVEL[level])
</script>

<template>
  <Tooltip v-if="compact">
    <TooltipTrigger as-child>
      <component :is="icon" class="size-3.5 shrink-0 text-muted-foreground" />
    </TooltipTrigger>
    <TooltipContent>
      {{ label }}
    </TooltipContent>
  </Tooltip>
  <Badge v-else :variant class="gap-1">
    <component :is="icon" class="size-3" />
    {{ label }}
  </Badge>
</template>
