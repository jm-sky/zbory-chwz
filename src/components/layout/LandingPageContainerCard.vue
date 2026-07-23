<script setup lang="ts">
defineProps<{
  label: string
  to: string
  containersCount: number
}>()
</script>

<template>
  <RouterLink
    :to
    class="cursor-pointer bg-background rounded-lg border p-4 text-center hover:scale-102 hover:-translate-y-0.5 hover:shadow-lg transition-all duration-300"
  >
    <div class="text-3xl font-bold text-primary mb-2">
      {{ containersCount }}
    </div>
    <div class="text-muted-foreground text-sm">
      {{ label }}
    </div>
  </RouterLink>
</template>
