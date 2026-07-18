<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ButtonGroup } from '@/components/ui/button-group'
import Button from '@/components/ui/button/Button.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { WEEKDAY_KEYS, type WeekdayKey } from '../constants/weekdays'

const emit = defineEmits<{
  add: [entries: Array<{ day: string, time: string }>]
}>()

const { t } = useI18n()

const selectedDays = ref<Set<WeekdayKey>>(new Set())
const time = ref<string>('')

const canAdd = computed<boolean>(() => selectedDays.value.size > 0 && !!time.value)

function toggleDay(key: WeekdayKey) {
  const next = new Set(selectedDays.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedDays.value = next
}

function handleAdd() {
  if (!canAdd.value) return
  const entries = WEEKDAY_KEYS
    .filter(key => selectedDays.value.has(key))
    .map(key => ({ day: t(`congregations.edit.weekdays.${key}`), time: time.value }))
  emit('add', entries)
  selectedDays.value = new Set()
  time.value = ''
}
</script>

<template>
  <div class="space-y-3 rounded-lg border bg-muted/30 p-4">
    <div>
      <p class="text-sm font-medium">
        {{ t('congregations.edit.serviceTimeQuickAdd.title', 'Szybkie dodawanie') }}
      </p>
      <p class="text-sm text-muted-foreground">
        {{ t('congregations.edit.serviceTimeQuickAdd.hint', 'Zaznacz dni, wpisz godzinę i dodaj kilka wpisów naraz.') }}
      </p>
    </div>

    <div class="flex flex-wrap items-end gap-3">
      <ButtonGroup>
        <Button
          v-for="key in WEEKDAY_KEYS"
          :key="key"
          type="button"
          size="sm"
          :variant="selectedDays.has(key) ? 'default' : 'outline'"
          :class="cn('w-12')"
          :aria-pressed="selectedDays.has(key)"
          @click="toggleDay(key)"
        >
          {{ t(`congregations.edit.weekdaysShort.${key}`) }}
        </Button>
      </ButtonGroup>

      <div class="space-y-1">
        <Label class="text-xs text-muted-foreground">
          {{ t('congregations.edit.serviceTimeQuickAdd.time', 'Godzina') }}
        </Label>
        <Input v-model="time" type="time" class="w-32" />
      </div>

      <Button
        type="button"
        variant="secondary"
        :disabled="!canAdd"
        @click="handleAdd"
      >
        {{ t('congregations.edit.serviceTimeQuickAdd.add', 'Dodaj zaznaczone dni') }}
      </Button>
    </div>
  </div>
</template>
