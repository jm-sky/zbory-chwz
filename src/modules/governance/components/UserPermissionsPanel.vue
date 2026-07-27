<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { churchApiService } from '@/modules/congregations/services/churchApiService'
import { useHandleError } from '@/shared/composables/useHandleError'
import { usePermissions } from '@/shared/composables/usePermissions'
import type { IUserPermission, PermissionEffectState } from '../types/governance.types'
import { governanceApiService } from '../services/governanceApiService'
import { inheritedPermissions as computeInheritedPermissions, isWideScope as computeIsWideScope, permissionCatalog as computePermissionCatalog } from '../utils/permissionState'
import type { IGrantableRole } from '@/modules/congregations/types/church.types'

const { userId, scopeType, scopeId } = defineProps<{
  userId: string
  scopeType: string
  scopeId: string
}>()

const open = defineModel<boolean>('open', { required: true })

const { t } = useI18n()
const { handleError } = useHandleError()
const { canInScope } = usePermissions()

const roles = ref<IGrantableRole[]>([])
const exceptions = ref<IUserPermission[]>([])
const roleAssignments = ref<{ roleName: string }[]>([])
const loading = ref(true)
const savingPermission = ref<string | null>(null)

const isWideScope = computed<boolean>(() => computeIsWideScope(scopeType))

const permissionCatalog = computed<string[]>(() => computePermissionCatalog(roles.value))

const inheritedPermissions = computed<Set<string>>(() =>
  computeInheritedPermissions(roles.value, roleAssignments.value.map(a => a.roleName)),
)

function exceptionFor(permission: string): IUserPermission | undefined {
  return exceptions.value.find(e => e.permission === permission)
}

function stateFor(permission: string): PermissionEffectState {
  return exceptionFor(permission)?.effect ?? 'inherited'
}

function sourceLabel(permission: string): string {
  if (!inheritedPermissions.value.has(permission)) {
    return t('governance.permissions.noSource', '—')
  }
  const grantingRole = roleAssignments.value.find((a) => {
    const role = roles.value.find(r => r.name === a.roleName)
    return role?.permissions.includes(permission)
  })
  return grantingRole ? t(`congregations.people.roles.${grantingRole.roleName}`, grantingRole.roleName) : t('governance.permissions.noSource', '—')
}

async function load() {
  loading.value = true
  try {
    const [rolesCatalog, userExceptions, assignments] = await Promise.all([
      churchApiService.listRoles(),
      governanceApiService.listUserPermissions(userId, scopeType, scopeId),
      governanceApiService.listRoleAssignments(scopeType, scopeId),
    ])
    roles.value = rolesCatalog
    exceptions.value = userExceptions
    roleAssignments.value = assignments.filter(a => a.userId === userId).map(a => ({ roleName: a.roleName }))
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) void load()
}, { immediate: true })

async function setState(permission: string, next: PermissionEffectState) {
  savingPermission.value = permission
  try {
    if (next === 'inherited') {
      const existing = exceptionFor(permission)
      if (existing) {
        await governanceApiService.deleteUserPermission(existing.id)
        exceptions.value = exceptions.value.filter(e => e.id !== existing.id)
      }
    } else {
      const updated = await governanceApiService.upsertUserPermission({
        userId,
        scopeType,
        scopeId,
        permission,
        effect: next,
      })
      exceptions.value = [...exceptions.value.filter(e => e.permission !== permission), updated]
    }
    toast.success(t('governance.permissions.saveSuccess', 'Zapisano'))
  } catch (error) {
    handleError(error, { fallbackMessage: t('governance.permissions.saveError', 'Nie udało się zapisać') })
  } finally {
    savingPermission.value = null
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{{ t('governance.permissions.title', 'Uprawnienia użytkownika') }}</DialogTitle>
        <DialogDescription>
          {{ t('governance.permissions.subtitle', 'Nadpisz pojedyncze uprawnienia dla tego użytkownika w tym zasięgu.') }}
        </DialogDescription>
      </DialogHeader>

      <div v-if="isWideScope" class="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-900 dark:text-amber-100">
        <AlertTriangle class="mt-0.5 size-4 shrink-0" />
        <span>{{ t('governance.permissions.wideScopeWarning', 'Wyjątek "odmów" w tym zasięgu wygrywa we wszystkich zborach poniżej — obowiązuje w całym łańcuchu.') }}</span>
      </div>

      <div v-if="loading" class="text-sm text-muted-foreground">
        {{ t('common.loading', 'Ładowanie...') }}
      </div>

      <ul v-else class="divide-y">
        <li
          v-for="permission in permissionCatalog"
          :key="permission"
          class="flex items-center justify-between gap-3 py-2"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-medium">
              {{ permission }}
            </p>
            <p class="truncate text-xs text-muted-foreground">
              {{ t('governance.permissions.sourceLabel', 'Skąd:') }} {{ sourceLabel(permission) }}
            </p>
          </div>
          <Select
            :model-value="stateFor(permission)"
            :disabled="!canInScope(permission, scopeType, scopeId) || savingPermission === permission"
            @update:model-value="setState(permission, $event as PermissionEffectState)"
          >
            <SelectTrigger class="w-36 shrink-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="inherited">
                {{ t('governance.permissions.state.inherited', 'Dziedziczone') }}
              </SelectItem>
              <SelectItem value="allow">
                {{ t('governance.permissions.state.allow', 'Zezwól') }}
              </SelectItem>
              <SelectItem value="deny">
                {{ t('governance.permissions.state.deny', 'Odmów') }}
              </SelectItem>
            </SelectContent>
          </Select>
        </li>
      </ul>
    </DialogContent>
  </Dialog>
</template>
