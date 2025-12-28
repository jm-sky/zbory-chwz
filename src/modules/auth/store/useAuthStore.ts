// modules/auth/store/useAuthStore.ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useUserStore } from '@/modules/user/store/useUserStore'
import { JWT_STORE_KEY } from '@/shared/config/config'
import { setSentryUser } from '@/shared/services/sentry'
import type { User } from '@/modules/auth/types/user.type'

const TWO_FACTOR_TOKEN_KEY = 'vbr_2fa_token'
const REFRESH_TOKEN_KEY = 'vbr_refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem(JWT_STORE_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_TOKEN_KEY))
  const twoFactorToken = ref<string | null>(localStorage.getItem(TWO_FACTOR_TOKEN_KEY))
  const twoFactorMethods = ref<string[]>([]) // Available 2FA methods from login response
  const preferredTwoFactorMethod = ref<string | null>(null) // Preferred method from login response

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isTwoFactorPending = computed(() => !!twoFactorToken.value && !token.value)

  const setToken = (newToken: string) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem(JWT_STORE_KEY, newToken)
    } else {
      localStorage.removeItem(JWT_STORE_KEY)
    }
    // Clear 2FA token when access token is set (2FA verification completed)
    if (newToken) {
      clearTwoFactorToken()
    }
  }

  const setTwoFactorToken = (newToken: string, methods?: string[], preferredMethod?: string | null) => {
    twoFactorToken.value = newToken
    if (newToken) {
      localStorage.setItem(TWO_FACTOR_TOKEN_KEY, newToken)
      if (methods) {
        twoFactorMethods.value = methods
      }
      if (preferredMethod !== undefined) {
        preferredTwoFactorMethod.value = preferredMethod
      }
    } else {
      localStorage.removeItem(TWO_FACTOR_TOKEN_KEY)
      twoFactorMethods.value = []
      preferredTwoFactorMethod.value = null
    }
  }

  const setUser = (newUser: User | null) => {
    user.value = newUser

    // Set Sentry user context for error tracking
    if (newUser) {
      setSentryUser({
        id: newUser.id,
        email: newUser.email,
        username: newUser.name,
      })
    } else {
      setSentryUser(null)
    }

    // Sync with userStore for profile page
    if (newUser) {
      const userStore = useUserStore()
      userStore.setUser({
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        avatarUrl: newUser.avatarUrl,
        isAdmin: newUser.isAdmin,
        isOwner: newUser.isOwner,
        isPremium: newUser.isPremium,
        createdAt: newUser.createdAt,
        updatedAt: new Date().toISOString(),
      })
    }
  }

  const setRefreshToken = (newRefreshToken: string | null) => {
    refreshToken.value = newRefreshToken
    if (newRefreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken)
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY)
    }
  }

  const clearToken = () => {
    token.value = null
    localStorage.removeItem(JWT_STORE_KEY)
  }

  const clearRefreshToken = () => {
    refreshToken.value = null
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  const clearTwoFactorToken = () => {
    twoFactorToken.value = null
    localStorage.removeItem(TWO_FACTOR_TOKEN_KEY)
  }

  const clearUser = () => {
    user.value = null
    // Reset userStore to default user on logout
    const userStore = useUserStore()
    userStore.initializeDefaultUser()
  }

  const logout = () => {
    clearToken()
    clearRefreshToken()
    clearTwoFactorToken()
    clearUser()
    // Clear Sentry user context on logout
    setSentryUser(null)
  }

  return {
    user,
    token,
    refreshToken,
    twoFactorToken,
    twoFactorMethods,
    preferredTwoFactorMethod,
    isAuthenticated,
    isTwoFactorPending,
    setToken,
    setRefreshToken,
    clearToken,
    clearRefreshToken,
    setTwoFactorToken,
    clearTwoFactorToken,
    setUser,
    clearUser,
    logout,
  }
})
