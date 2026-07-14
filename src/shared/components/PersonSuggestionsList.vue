<script setup lang="ts">
import type { IPersonSummary } from '../types/person.type'
import { formatPhoneNumber } from '../utils/formatPhone'

defineProps<{
  suggestions: IPersonSummary[]
}>()

const emit = defineEmits<{
  select: [person: IPersonSummary]
}>()

function personLabel(person: IPersonSummary): string {
  const name = [person.firstName, person.lastName].filter(Boolean).join(' ')
  return name || person.email || formatPhoneNumber(person.phone) || '—'
}

function personDetail(person: IPersonSummary): string {
  return [person.email, formatPhoneNumber(person.phone)].filter(Boolean).join(' · ')
}
</script>

<template>
  <ul
    v-if="suggestions.length > 0"
    class="absolute z-50 mt-1 max-h-56 w-full min-w-64 overflow-auto rounded-md border bg-popover shadow-md"
  >
    <li v-for="person in suggestions" :key="person.id">
      <button
        type="button"
        class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-sm hover:bg-accent"
        @mousedown.prevent="emit('select', person)"
      >
        <span class="font-medium">{{ personLabel(person) }}</span>
        <span v-if="personDetail(person)" class="text-xs text-muted-foreground">
          {{ personDetail(person) }}
        </span>
      </button>
    </li>
  </ul>
</template>
