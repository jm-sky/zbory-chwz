<script setup lang="ts">
import { Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import PersonBrowserPanel from '../components/PersonBrowserPanel.vue'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <div>
        <h1 class="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Users class="size-8 text-primary" />
          {{ t('directory.persons.title', 'Przeglądarka osób') }}
        </h1>
        <p class="text-muted-foreground mt-2">
          {{ t('directory.persons.subtitle', 'Przeglądaj, edytuj i scalaj duplikaty osób w Twoim zasięgu') }}
        </p>
      </div>

      <PersonBrowserPanel />
    </div>
  </AuthenticatedLayout>
</template>
