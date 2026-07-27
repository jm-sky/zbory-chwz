<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Alert from '@/components/ui/alert/Alert.vue'
import AlertDescription from '@/components/ui/alert/AlertDescription.vue'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import GuestLayoutCentered from '@/layouts/GuestLayoutCentered.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { acceptInviteSchema } from '@/modules/auth/validation/acceptInvite.schema'
import { useHandleError } from '@/shared/composables/useHandleError'
import { AuthRoutePaths } from '../config/routes'
import type { AcceptInviteData } from '@/modules/auth/types/user.type'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { acceptInvite, isAcceptInviteLoading } = useAuth()
const { handleError } = useHandleError()

const token = computed(() => (route.query.token as string | null) ?? '')
const isExpiredOrInvalid = ref(false)
const successMessage = ref('')

const { handleSubmit, setErrors } = useForm({
  validationSchema: toTypedSchema(acceptInviteSchema),
  initialValues: {
    token: token.value,
    password: '',
    passwordConfirmation: '',
  },
})

const onSubmit = handleSubmit(async (values: AcceptInviteData) => {
  isExpiredOrInvalid.value = false
  try {
    const response = await acceptInvite(values)
    successMessage.value = response.message || t('auth.accept_invite_page.success')
    setTimeout(() => void router.push(AuthRoutePaths.login), 2000)
  } catch (error: unknown) {
    isExpiredOrInvalid.value = true
    handleError(error, { setErrors })
  }
})
</script>

<template>
  <GuestLayoutCentered>
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="text-center text-3xl font-extrabold text-foreground">
          {{ t('auth.accept_invite_page.title') }}
        </h2>
        <p class="mt-2 text-center text-sm text-muted-foreground">
          {{ t('auth.accept_invite_page.subtitle') }}
        </p>
      </div>

      <div class="bg-card py-8 px-6 shadow-lg rounded-lg space-y-4">
        <Alert v-if="successMessage" variant="success">
          <AlertDescription>
            {{ successMessage }}
          </AlertDescription>
        </Alert>

        <Alert v-if="isExpiredOrInvalid" variant="destructive">
          <AlertDescription>
            {{ t('auth.accept_invite_page.invalid_or_expired') }}
          </AlertDescription>
        </Alert>

        <form v-if="!successMessage" class="space-y-4" @submit="onSubmit">
          <FormField v-slot="{ componentField }" name="token">
            <FormItem>
              <FormControl>
                <Input type="hidden" v-bind="componentField" />
              </FormControl>
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="password">
            <FormItem>
              <FormLabel required>
                {{ t('auth.new_password') }}
              </FormLabel>
              <FormControl>
                <Input type="password" :placeholder="t('auth.form.new_password_placeholder')" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="passwordConfirmation">
            <FormItem>
              <FormLabel required>
                {{ t('auth.password_confirm') }}
              </FormLabel>
              <FormControl>
                <Input type="password" :placeholder="t('auth.form.password_confirm_placeholder')" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <Button type="submit" class="w-full" :loading="isAcceptInviteLoading">
            {{ t('auth.accept_invite_page.submit_button') }}
          </Button>
        </form>
      </div>

      <div class="text-center">
        <RouterLink to="/auth/login" class="text-sm text-primary hover:underline">
          {{ t('auth.accept_invite_page.back_to_login') }}
        </RouterLink>
      </div>
    </div>
  </GuestLayoutCentered>
</template>
