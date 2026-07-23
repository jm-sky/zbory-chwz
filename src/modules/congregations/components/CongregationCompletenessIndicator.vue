<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import Progress from '@/components/ui/progress/Progress.vue'
import type { CompletenessFieldKey } from '../utils/congregationCompleteness'

const { t } = useI18n()

const { score, missingFields = [], compact = false } = defineProps<{
  score: number
  missingFields?: CompletenessFieldKey[]
  compact?: boolean
}>()

const tone = computed<'low' | 'medium' | 'high'>(() => {
  if (score < 40) return 'low'
  if (score < 75) return 'medium'
  return 'high'
})

const badgeVariant = computed(() => ({ low: 'destructive', medium: 'outline', high: 'success' })[tone.value] as 'destructive' | 'outline' | 'success')
const toneTextClass = computed(() => ({
  low: 'text-destructive',
  medium: 'text-amber-600 dark:text-amber-400',
  high: 'text-success',
})[tone.value])
const indicatorClass = computed(() => ({
  low: 'bg-destructive',
  medium: 'bg-amber-500',
  high: 'bg-success',
})[tone.value])

const missingFieldLabels = computed<string[]>(() => missingFields.map((field) => t(`congregations.completeness.fields.${field}`)))
const missingTooltip = computed<string | undefined>(() =>
  missingFieldLabels.value.length ? `${t('congregations.completeness.missingPrefix')} ${missingFieldLabels.value.join(', ')}` : undefined,
)
</script>

<template>
  <Badge v-if="compact" v-tooltip="missingTooltip" :variant="badgeVariant">
    {{ score }}%
  </Badge>
  <div v-else class="flex flex-col gap-1.5">
    <div class="flex items-center justify-between text-sm">
      <span class="font-medium">{{ t('congregations.completeness.title') }}</span>
      <span :class="['font-semibold', toneTextClass]">{{ score }}%</span>
    </div>
    <Progress :model-value="score" :indicator-class="indicatorClass" />
    <p v-if="missingFieldLabels.length" class="text-muted-foreground text-xs">
      {{ t('congregations.completeness.missingPrefix') }} {{ missingFieldLabels.join(', ') }}
    </p>
  </div>
</template>
