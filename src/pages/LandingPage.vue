<script setup lang="ts">
import { Church } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import MainLayout from '@/layouts/MainLayout.vue'
import CongregationsList from '@/modules/congregations/components/CongregationsList.vue'

const { t } = useI18n()
</script>

<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <Church class="size-8 text-primary" />
        <h1 class="text-3xl font-bold">
          {{ t('congregations.list.title', 'Zbory CHWZ') }}
        </h1>
      </div>

      <!-- Description -->
      <p class="text-muted-foreground">
        {{ t('congregations.list.description', 'Lista zborów Chrześcijańskiej Wspólnoty Wolnych Zielonoświątkowców') }}
      </p>

      <!-- Congregations List -->
      <CongregationsList />
    </div>
  </MainLayout>
</template>
