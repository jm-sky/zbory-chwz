<script setup lang="ts">
import { Church, LogIn } from 'lucide-vue-next'
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import WelcomeQuickActions from '@/components/layout/WelcomeQuickActions.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { PublicRoutePaths } from '@/router/publicRoutes'
import { usePermissions } from '@/shared/composables/usePermissions'

const { t } = useI18n()
const { isAuthenticated } = useAuth()
const { canAccessAdminPanel } = usePermissions()
const router = useRouter()

// Redirect regular users to congregations list (landing page)
onMounted(() => {
  if (isAuthenticated.value && !canAccessAdminPanel.value) {
    router.replace(PublicRoutePaths.landing)
  }
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="container mx-auto p-6">
      <h1 class="mb-6 text-3xl font-bold">
        {{ t('navigation.dashboard') }}
      </h1>

      <!-- Welcome section for authenticated users -->
      <div v-if="isAuthenticated" class="mb-8">
        <div class="rounded-lg border bg-card p-6">
          <h2 class="mb-4 text-xl font-semibold">
            {{ t('common.welcome') }}
          </h2>
          <p class="text-muted-foreground">
            Witaj w systemie zarządzania zborami CHWZ. W przyszłości tutaj zobaczysz statystyki i
            szybki dostęp do swoich zborów.
          </p>
        </div>
      </div>

      <!-- Guest welcome section -->
      <div v-else class="space-y-6">
        <div class="rounded-lg border bg-card p-6">
          <div class="mb-4 flex items-center gap-3">
            <Church class="size-8 text-primary" />
            <h2 class="text-2xl font-semibold">
              Zbory CHWZ
            </h2>
          </div>
          <p class="mb-4 text-muted-foreground">
            System zarządzania i publicznej prezentacji zborów Chrześcijańskiej Wspólnoty Wolnych
            Zielonoświątkowców.
          </p>

          <div class="flex flex-wrap gap-4">
            <ButtonLink :to="AuthRoutePaths.login">
              <LogIn class="size-4" />
              {{ t('auth.login') }}
            </ButtonLink>
          </div>
        </div>

        <WelcomeQuickActions />
      </div>
    </div>
  </AuthenticatedLayout>
</template>
