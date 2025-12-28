<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'

const { t } = useI18n()
</script>

<template>
  <Badge variant="premium">
    <slot>
      {{ t('premium.premiumFeature') }}
    </slot>
  </Badge>
</template>
