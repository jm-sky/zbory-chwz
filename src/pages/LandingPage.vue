<script setup lang="ts">
import { Church } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import WelcomeQuickActions from '@/components/layout/WelcomeQuickActions.vue'
import LandingLayout from '@/layouts/LandingLayout.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { config } from '@/shared/config/config'

const { t } = useI18n()
const router = useRouter()
const { isAuthenticated, user } = useAuth()

// If backend is disabled, redirect to home (offline mode)
if (!config.backend.enabled) {
  router.replace({ name: 'home' })
}
</script>

<template>
  <LandingLayout>
    <div class="w-full max-w-2xl space-y-8 text-center">
      <!-- Logo/Icon -->
      <div class="flex justify-center">
        <div class="rounded-full bg-primary/10 p-8">
          <Church class="size-20 text-primary" />
        </div>
      </div>

      <!-- Heading -->
      <div class="space-y-4">
        <p v-if="isAuthenticated && user" class="text-2xl font-semibold text-muted-foreground">
          {{ t('landing.welcomeBack', { name: user.name }) }}
        </p>
        <h1 class="text-5xl font-bold tracking-tight">
          Zbory CHWZ
        </h1>
        <p class="mx-auto max-w-lg text-xl text-muted-foreground">
          Aplikacja do zarządzania i publicznej prezentacji zborów Chrześcijańskiej Wspólnoty
          Wolnych Zielonoświątkowców
        </p>
      </div>
    </div>

    <!-- Features -->
    <div class="w-full max-w-2xl space-y-8 text-center">
      <div class="grid grid-cols-1 gap-6 py-4 md:grid-cols-3">
        <div class="space-y-2">
          <h3 class="text-lg font-semibold">
            Zarządzanie
          </h3>
          <p class="text-sm text-muted-foreground">
            Zarządzaj danymi swoich zborów w jednym miejscu
          </p>
        </div>
        <div class="space-y-2">
          <h3 class="text-lg font-semibold">
            Publiczna prezentacja
          </h3>
          <p class="text-sm text-muted-foreground">
            Udostępniaj informacje o zborach publicznie
          </p>
        </div>
        <div class="space-y-2">
          <h3 class="text-lg font-semibold">
            Multi-tenant
          </h3>
          <p class="text-sm text-muted-foreground">
            Różne role i uprawnienia dla użytkowników
          </p>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <WelcomeQuickActions />
  </LandingLayout>
</template>
