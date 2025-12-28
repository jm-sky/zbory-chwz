<script setup lang="ts">
import { User } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Avatar from '@/components/ui/avatar/Avatar.vue'
import AvatarFallback from '@/components/ui/avatar/AvatarFallback.vue'
import AvatarImage from '@/components/ui/avatar/AvatarImage.vue'
import ButtonLink from '@/components/ui/button-link/ButtonLink.vue'
import { Card, CardContent } from '@/components/ui/card'
import UserRoleBadge from '@/components/ui/UserRoleBadge.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { getInitials } from '@/shared/utils/getInitials'
import type { IUser } from '../types/user.types'
import { UserRoutePaths } from '../routes'
import { userApiService } from '../services/userApiService'

const route = useRoute()
const { t } = useI18n()
const { user: currentUser } = useAuth()

const userId = route.params.userId as string
const user = ref<IUser | null>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)

const isCurrentUser = computed(() => user.value?.id === currentUser.value?.id)

const initials = computed(() => {
  if (user.value?.name) {
    return getInitials(user.value.name)
  }
  if (user.value?.email) {
    return user.value.email.substring(0, 2).toUpperCase()
  }
  return 'U'
})

onMounted(async () => {
  try {
    // Fetch public user profile using service
    user.value = await userApiService.getPublicUser(userId)
  } catch (err: unknown) {
    console.error('Failed to load public user profile:', err)
    const errorResponse = err as { response?: { status?: number } }
    if (errorResponse.response?.status === 404) {
      error.value = t('user.publicProfile.not_found')
    } else if (errorResponse.response?.status === 403) {
      error.value = t('user.publicProfile.not_public')
    } else {
      error.value = t('user.publicProfile.error')
    }
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <AuthenticatedLayout>
    <div v-if="isLoading" class="space-y-6">
      <div class="h-32 bg-muted rounded animate-pulse" />
    </div>

    <div v-else-if="error" class="space-y-6">
      <div class="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-6 text-center">
        <User class="size-12 mx-auto mb-4 text-destructive/50" />
        <h2 class="text-xl font-semibold mb-2">
          {{ t('user.publicProfile.error_title') }}
        </h2>
        <p>{{ error }}</p>
      </div>
    </div>

    <div v-else-if="user" class="space-y-6 w-full max-w-full">
      <!-- User Profile Header -->
      <Card>
        <CardContent>
          <div class="flex flex-col sm:flex-row items-center sm:items-stretch gap-4 sm:gap-6">
            <Avatar class="size-20 sm:size-24 ring-1 ring-border shrink-0">
              <AvatarImage :src="user.avatarUrl ?? ''" :alt="user.name" />
              <AvatarFallback class="bg-muted text-muted-foreground text-xl sm:text-2xl font-semibold">
                {{ initials }}
              </AvatarFallback>
            </Avatar>
            <div class="flex flex-col items-start text-center sm:text-left flex-1">
              <div class="flex items-center gap-2 flex-wrap justify-center sm:justify-start">
                <h1 class="text-2xl sm:text-3xl font-bold">
                  {{ user.name }}
                </h1>
                <UserRoleBadge
                  :is-admin="user.isAdmin"
                  :is-owner="user.isOwner"
                  :is-premium="user.isPremium"
                />
              </div>
              <p v-if="user.emailPublic && user.email" class="flex items-center justify-center sm:justify-start w-full text-muted-foreground text-sm sm:text-base break-all mt-2">
                {{ user.email }}
              </p>
            </div>
            <div v-if="isCurrentUser">
              <ButtonLink :to="UserRoutePaths.profileEdit">
                {{ t('common.edit') }}
              </ButtonLink>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </AuthenticatedLayout>
</template>
