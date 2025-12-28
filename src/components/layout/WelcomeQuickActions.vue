<script setup lang="ts">
import { LogInIcon, UserPlusIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { config } from '@/shared/config/config'
import ButtonLink from '../ui/button-link/ButtonLink.vue'
import Separator from '../ui/separator/Separator.vue'
import type { HTMLAttributes } from 'vue'

const { t } = useI18n()
const { isAuthenticated } = useAuth()

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div :class="cn('flex flex-col gap-4 items-center justify-center', props.class)">
    <!-- Welcome message for authenticated users -->
    <div class="text-center space-y-2">
      <h2 class="text-2xl font-semibold">
        {{ t('common.welcome', 'Welcome') }}
      </h2>
      <p class="text-muted-foreground">
        {{ t('common.welcomeMessage', 'Get started by exploring the application') }}
      </p>
    </div>

    <Separator v-if="!isAuthenticated && config.backend.enabled" />

    <!-- Login, Register (only if not authenticated) -->
    <div v-if="!isAuthenticated && config.backend.enabled" class="flex flex-col items-center justify-center sm:flex-row gap-4 w-full mt-2">
      <ButtonLink
        size="lg"
        variant="outline"
        class="flex-1"
        :to="AuthRoutePaths.login"
      >
        <LogInIcon class="size-5" />
        {{ t('auth.login', 'Log In') }}
      </ButtonLink>
      <ButtonLink
        size="lg"
        variant="outline"
        class="flex-1"
        :to="AuthRoutePaths.register"
      >
        <UserPlusIcon class="size-5" />
        {{ t('auth.register', 'Sign Up') }}
      </ButtonLink>
    </div>
  </div>
</template>
