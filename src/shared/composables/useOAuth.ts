import { ref } from 'vue'
import { authService } from '@/modules/auth/services/authService'
import { config } from '@/shared/config/config'

export function useOAuth() {
  const isPending = ref(false)
  const error = ref<Error | null>(null)

  const initiateGoogleLogin = async () => {
    if (!config.oauth.google.enabled) {
      error.value = new Error('Google OAuth not configured')
      return
    }

    isPending.value = true
    error.value = null

    try {
      const response = await authService.getOAuthAuthUrl('google')

      // Store state for CSRF verification
      sessionStorage.setItem('oauth_state', response.state)

      // Redirect to Google
      window.location.href = response.authUrl
    }
    catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to initiate login')
      isPending.value = false
    }
  }

  const initiateFacebookLogin = async () => {
    if (!config.oauth.facebook.enabled) {
      error.value = new Error('Facebook OAuth not configured')
      return
    }

    isPending.value = true
    error.value = null

    try {
      const response = await authService.getOAuthAuthUrl('facebook')

      // Store state for CSRF verification
      sessionStorage.setItem('oauth_state', response.state)

      // Redirect to Facebook
      window.location.href = response.authUrl
    }
    catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to initiate login')
      isPending.value = false
    }
  }

  return {
    error,
    initiateFacebookLogin,
    initiateGoogleLogin,
    isEnabled: config.oauth.google.enabled,
    isFacebookEnabled: config.oauth.facebook.enabled,
    isPending,
  }
}
