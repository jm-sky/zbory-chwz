<script setup lang="ts">
import { Shield } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/button/Button.vue'
import Card from '@/components/ui/card/Card.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { GroupsRoutePaths } from '@/modules/groups/routes'
import { usePermissions } from '@/shared/composables/usePermissions'
import { AdminRoutePaths } from '../routes'

const { t } = useI18n()
const { canAccessAdminPanel } = usePermissions()

if (!canAccessAdminPanel.value) {
  // Redirect will be handled by router guard
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <!-- Header -->
      <div>
        <h1 class="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Shield class="size-8 text-primary" />
          {{ t('admin.dashboard.title', 'Admin Dashboard') }}
        </h1>
        <p class="text-muted-foreground mt-2">
          {{ t('admin.dashboard.subtitle', 'Manage users and system settings') }}
        </p>
      </div>

      <!-- Quick Links -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card class="p-6">
          <div class="flex flex-col gap-4 flex-1">
            <div class="flex-1">
              <h3 class="text-lg font-semibold">
                {{ t('admin.dashboard.users.title', 'Users') }}
              </h3>
              <p class="text-sm text-muted-foreground">
                {{ t('admin.dashboard.users.description', 'Manage user accounts and permissions') }}
              </p>
            </div>
            <RouterLink :to="AdminRoutePaths.users">
              <Button class="w-full">
                {{ t('admin.dashboard.users.button', 'Manage Users') }}
              </Button>
            </RouterLink>
          </div>
        </Card>
        <Card class="p-6">
          <div class="flex flex-col gap-4 flex-1">
            <div class="flex-1">
              <h3 class="text-lg font-semibold">
                {{ t('admin.dashboard.congregations.title', 'Congregations') }}
              </h3>
              <p class="text-sm text-muted-foreground">
                {{ t('admin.dashboard.congregations.description', 'Manage congregations and their members') }}
              </p>
            </div>
            <RouterLink :to="AdminRoutePaths.congregations">
              <Button class="w-full">
                {{ t('admin.dashboard.congregations.button', 'Manage Congregations') }}
              </Button>
            </RouterLink>
          </div>
        </Card>
        <Card class="p-6">
          <div class="flex flex-col gap-4 flex-1">
            <div class="flex-1">
              <h3 class="text-lg font-semibold">
                {{ t('groups.list.title', 'Grupy ludzi') }}
              </h3>
              <p class="text-sm text-muted-foreground">
                {{ t('groups.list.subtitle', 'Struktury organizacyjne niezależne od pojedynczego zboru') }}
              </p>
            </div>
            <RouterLink :to="GroupsRoutePaths.list">
              <Button class="w-full">
                {{ t('groups.list.title', 'Grupy ludzi') }}
              </Button>
            </RouterLink>
          </div>
        </Card>
      </div>
    </div>
  </AuthenticatedLayout>
</template>
