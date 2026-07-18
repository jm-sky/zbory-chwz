import { startAuthentication, startRegistration } from '@simplewebauthn/browser'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
// modules/auth/composables/useWebAuthn.ts
import { twoFactorService } from '@/modules/auth/services/twoFactorService'
import { twoFactorQueryKeys } from './useTwoFactor'
import type {
  ITwoFactorService,
  WebAuthnRegisterRequest,
} from '@/modules/auth/types/twoFactor.type'


/**
 * Hook for registering a new passkey
 */
export function useRegisterPasskey(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: WebAuthnRegisterRequest) => {
      const svc = service ?? twoFactorService

      // Step 1: Get registration options from backend
      const registerResponse = await svc.registerPasskey(request)

      // Step 2: Start WebAuthn registration ceremony
      const credential = await startRegistration({
        optionsJSON: registerResponse.options,
      })

      // Step 3: Complete registration with backend
      return await svc.completePasskeyRegistration(
        request.name,
        registerResponse.registrationToken,
        credential
      )
    },
    onSuccess: async () => {
      // Invalidate all 2FA queries to refresh status and passkey list
      await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
    },
  })
}

/**
 * Hook for verifying with a passkey during login
 */
export function useVerifyPasskey(service?: ITwoFactorService) {
  return useMutation({
    mutationFn: async () => {
      const svc = service ?? twoFactorService

      // Step 1: Get verification options from backend
      const verifyResponse = await svc.verifyPasskey()

      // Step 2: Start WebAuthn authentication ceremony
      const credential = await startAuthentication({
        optionsJSON: verifyResponse.options,
      })

      // Step 3: Complete verification with backend
      return await svc.completePasskeyVerification(
        verifyResponse.challengeToken,
        credential
      )
    },
  })
}

/**
 * Hook for deleting a passkey
 */
export function useDeletePasskey(service?: ITwoFactorService) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (passkeyId: string) => {
      return (service ?? twoFactorService).deletePasskey(passkeyId)
    },
    onSuccess: async () => {
      // Invalidate all 2FA queries to refresh status and passkey list
      await queryClient.invalidateQueries({ queryKey: twoFactorQueryKeys.all })
    },
  })
}
