<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'

const emit = defineEmits<{
  unlink: []
}>()

const { t } = useI18n()
</script>

<template>
  <Badge variant="secondary" class="gap-1 pr-1">
    {{ t('personSearch.personExists', 'Osoba już istnieje') }}
    <Button
      type="button"
      variant="ghost"
      size="icon"
      class="size-4"
      :aria-label="t('personSearch.unlink', 'Odepnij')"
      @click="emit('unlink')"
    >
      <X class="size-3" />
    </Button>
  </Badge>
</template>
