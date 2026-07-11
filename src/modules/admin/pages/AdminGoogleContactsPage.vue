<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { Contact, Link2, Mail, Phone, RefreshCw, Unlink } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IGoogleContactSuggestion } from '../types/googleContacts.types'
import { AdminRouteNames } from '../routes'
import { googleContactsApiService } from '../services/googleContactsApiService'

const GOOGLE_CONTACTS_OAUTH_STATE_KEY = 'google_contacts_oauth_state'

const { t } = useI18n()
const router = useRouter()
const { handleError } = useHandleError()
const queryClient = useQueryClient()

const connectionQueryKey = ['google-contacts', 'connection']

const { data: connection, isLoading: isConnectionLoading } = useQuery({
  queryKey: connectionQueryKey,
  queryFn: () => googleContactsApiService.getConnection(),
  staleTime: 60 * 1000,
})

const isConnecting = ref(false)
const contacts = ref<IGoogleContactSuggestion[]>([])
const totalFetched = ref<number | null>(null)
const isLoadingContacts = ref(false)
const hasLoadedContacts = computed(() => totalFetched.value !== null)

async function connect() {
  isConnecting.value = true
  try {
    const { authUrl, state } = await googleContactsApiService.getAuthUrl()
    sessionStorage.setItem(GOOGLE_CONTACTS_OAUTH_STATE_KEY, state)
    window.location.href = authUrl
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.connectError', 'Nie udało się rozpocząć łączenia z Google') })
    isConnecting.value = false
  }
}

const disconnectMutation = useMutation({
  mutationFn: () => googleContactsApiService.disconnect(),
  onSuccess: async () => {
    toast.success(t('admin.googleContacts.disconnectSuccess', 'Odłączono Google Contacts'))
    contacts.value = []
    totalFetched.value = null
    await queryClient.invalidateQueries({ queryKey: connectionQueryKey })
  },
  onError: (error: unknown) => handleError(error, { fallbackMessage: t('admin.googleContacts.disconnectError', 'Nie udało się odłączyć Google Contacts') }),
})

function disconnect() {
  if (!confirm(t('admin.googleContacts.disconnectConfirm', 'Odłączyć Google Contacts? Będzie trzeba połączyć ponownie, aby importować kontakty.'))) return
  disconnectMutation.mutate()
}

async function loadContacts() {
  isLoadingContacts.value = true
  try {
    const response = await googleContactsApiService.listContacts()
    contacts.value = response.contacts
    totalFetched.value = response.totalFetched
    if (response.matchedCount === 0) {
      toast.info(t('admin.googleContacts.noneFound', 'Nie znaleziono kontaktów pasujących do filtra „zbór”/„chwz”'))
    }
  } catch (error) {
    handleError(error, { fallbackMessage: t('admin.googleContacts.loadContactsError', 'Nie udało się wczytać kontaktów') })
  } finally {
    isLoadingContacts.value = false
  }
}

function goBack() {
  router.push({ name: AdminRouteNames.dashboard })
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="Contact"
        :label="t('admin.googleContacts.title', 'Google Contacts')"
        :description="t('admin.googleContacts.subtitle', 'Wczytaj zbory i osoby ze swojej książki kontaktów Google')"
        with-back-button
        @back="goBack"
      />

      <Card>
        <CardHeader>
          <CardTitle>{{ t('admin.googleContacts.connectionTitle', 'Połączenie') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div v-if="isConnectionLoading" class="text-sm text-muted-foreground">
            {{ t('admin.googleContacts.loading', 'Ładowanie...') }}
          </div>
          <div v-else class="flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <Badge :variant="connection?.connected ? 'success-outline' : 'outline'">
                {{ connection?.connected
                  ? t('admin.googleContacts.connected', 'Połączono')
                  : t('admin.googleContacts.notConnected', 'Niepołączono') }}
              </Badge>
              <span v-if="connection?.connected && connection.connectedAt" class="text-sm text-muted-foreground">
                {{ t('admin.googleContacts.connectedAt', 'od') }} {{ new Date(connection.connectedAt).toLocaleDateString() }}
              </span>
            </div>
            <div class="flex gap-2">
              <Button v-if="!connection?.connected" :disabled="isConnecting" @click="connect">
                <Link2 class="size-4" />
                {{ isConnecting
                  ? t('admin.googleContacts.connecting', 'Łączenie...')
                  : t('admin.googleContacts.connect', 'Połącz z Google') }}
              </Button>
              <Button
                v-else
                variant="outline"
                :disabled="disconnectMutation.isPending.value"
                @click="disconnect"
              >
                <Unlink class="size-4" />
                {{ t('admin.googleContacts.disconnect', 'Odłącz') }}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card v-if="connection?.connected">
        <CardHeader>
          <CardTitle>{{ t('admin.googleContacts.contactsTitle', 'Kontakty pasujące do filtra „zbór” / „chwz”') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex items-center gap-3">
            <Button :disabled="isLoadingContacts" @click="loadContacts">
              <RefreshCw class="size-4" />
              {{ isLoadingContacts
                ? t('admin.googleContacts.loadingContacts', 'Wczytywanie...')
                : t('admin.googleContacts.loadContacts', 'Wczytaj kontakty') }}
            </Button>
            <span v-if="hasLoadedContacts" class="text-sm text-muted-foreground">
              {{ t('admin.googleContacts.matched', 'Dopasowano') }} {{ contacts.length }} / {{ totalFetched }}
            </span>
          </div>

          <p v-if="hasLoadedContacts && contacts.length === 0" class="text-sm text-muted-foreground">
            {{ t('admin.googleContacts.empty', 'Brak kontaktów pasujących do filtra') }}
          </p>

          <div v-if="contacts.length > 0" class="space-y-3">
            <Card v-for="contact in contacts" :key="contact.resourceName" class="p-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="font-medium">
                      {{ contact.displayName ?? contact.organizationName ?? contact.resourceName }}
                    </span>
                    <Badge :variant="contact.suggestedType === 'church' ? 'primary-outline' : 'secondary'">
                      {{ contact.suggestedType === 'church'
                        ? t('admin.googleContacts.typeChurch', 'Zbór')
                        : t('admin.googleContacts.typePerson', 'Osoba') }}
                    </Badge>
                  </div>
                  <p v-if="contact.organizationName && contact.displayName" class="text-sm text-muted-foreground">
                    {{ contact.organizationName }}
                  </p>
                  <p v-if="contact.notes" class="text-sm text-muted-foreground">
                    {{ contact.notes }}
                  </p>
                </div>
                <div class="flex flex-col gap-1 text-sm text-muted-foreground">
                  <span v-for="email in contact.emailAddresses" :key="email" class="flex items-center gap-1">
                    <Mail class="size-3.5" />{{ email }}
                  </span>
                  <span v-for="phone in contact.phoneNumbers" :key="phone" class="flex items-center gap-1">
                    <Phone class="size-3.5" />{{ phone }}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>
  </AuthenticatedLayout>
</template>
