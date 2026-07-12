<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { AdminRoutePaths } from '../routes'
import { googleContactsApiService } from '../services/googleContactsApiService'

const GOOGLE_CONTACTS_OAUTH_STATE_KEY = 'google_contacts_oauth_state'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const error = ref<string | null>(null)

onMounted(async () => {
  const code = route.query.code as string | undefined
  const state = route.query.state as string | undefined
  const errorParam = route.query.error as string | undefined

  const redirectToIntegrationPage = () => {
    setTimeout(() => router.push(AdminRoutePaths.googleContacts), 2000)
  }

  if (errorParam) {
    error.value = t('admin.googleContacts.callback.deniedOrCancelled', 'Połączenie z Google zostało anulowane lub odrzucone.')
    redirectToIntegrationPage()
    return
  }

  if (!code || !state) {
    error.value = t('admin.googleContacts.callback.invalidParameters', 'Brak wymaganych parametrów w odpowiedzi Google.')
    redirectToIntegrationPage()
    return
  }

  const storedState = sessionStorage.getItem(GOOGLE_CONTACTS_OAUTH_STATE_KEY)
  if (!storedState || storedState !== state) {
    error.value = t('admin.googleContacts.callback.invalidState', 'Nieprawidłowy parametr state (możliwa próba CSRF).')
    redirectToIntegrationPage()
    return
  }
  sessionStorage.removeItem(GOOGLE_CONTACTS_OAUTH_STATE_KEY)

  try {
    await googleContactsApiService.completeConnection(code, state)
    toast.success(t('admin.googleContacts.callback.success', 'Połączono z Google Contacts'))
    await router.push(AdminRoutePaths.googleContacts)
  } catch (err: unknown) {
    let message = t('admin.googleContacts.callback.failed', 'Nie udało się połączyć z Google Contacts')
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message = axiosError.response.data.detail
      }
    }
    error.value = message
    toast.error(message)
    redirectToIntegrationPage()
  }
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="flex min-h-[60vh] items-center justify-center px-4">
      <Card class="w-full max-w-md">
        <CardHeader>
          <CardTitle v-if="error" class="text-destructive">
            {{ t('admin.googleContacts.callback.errorTitle', 'Połączenie nie powiodło się') }}
          </CardTitle>
          <CardTitle v-else class="flex items-center">
            <div class="mr-2 size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            {{ t('admin.googleContacts.callback.processing', 'Łączenie z Google Contacts...') }}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription>
            {{ error }}
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  </AuthenticatedLayout>
</template>
