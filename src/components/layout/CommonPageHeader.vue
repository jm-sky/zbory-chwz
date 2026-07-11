<script setup lang="ts">
import { cn } from '@/lib/utils'
import BackButton from './BackButton.vue'
import type { Component, HTMLAttributes } from 'vue'

const { icon, label, description } = defineProps<{
  icon?: Component
  label: string
  description?: string
  iconClass?: HTMLAttributes['class']
  withBackButton?: boolean
}>()

const emit = defineEmits<{
  back: []
}>()
</script>

<template>
  <div class="space-y-6">
    <!-- Above section (optional): back button + top actions -->
    <div v-if="$slots.above || withBackButton" class="flex items-center justify-between gap-3">
      <slot name="above">
        <slot name="back-button">
          <BackButton
            v-if="withBackButton"
            @click="emit('back')"
          />
        </slot>
        <slot name="top-actions" />
        <slot name="dropdown" />
      </slot>
    </div>

    <!-- Center section: title row + description -->
    <div>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex min-w-0 items-center gap-3 sm:flex-1">
          <slot name="before-icon" />
          <component
            :is="icon"
            v-if="icon"
            :class="cn('size-8 shrink-0 text-primary', iconClass)"
          />
          <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">
            {{ label }}
          </h1>
        </div>

        <div
          v-if="$slots.actions || $slots.dropdown"
          class="flex flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end"
        >
          <slot name="actions" />
          <slot name="dropdown" />
        </div>
      </div>

      <p v-if="description || $slots.description" class="mt-2 text-muted-foreground">
        <slot name="description">
          {{ description }}
        </slot>
      </p>
    </div>
  </div>
</template>
