<script setup lang="ts">
import { ShieldCheck } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import DataTable from '@/components/data-table/DataTable.vue'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import { Badge } from '@/components/ui/badge'
import Button from '@/components/ui/button/Button.vue'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import { usePermissions } from '@/shared/composables/usePermissions'
import type { GovernanceScopeType, IRoleAssignment } from '../types/governance.types'
import AclAuditSection from '../components/AclAuditSection.vue'
import RoleAssignmentDialog from '../components/RoleAssignmentDialog.vue'
import UserPermissionsPanel from '../components/UserPermissionsPanel.vue'
import { governanceApiService } from '../services/governanceApiService'
import type { ColumnDef } from '@tanstack/vue-table'
import type { PermissionScope } from '@/shared/composables/usePermissions'

const { t } = useI18n()
const { handleError } = useHandleError()
const { manageableScopes } = usePermissions()

const assignments = ref<IRoleAssignment[]>([])
const loading = ref(true)
const dialogOpen = ref(false)
const revokingId = ref<string | null>(null)
const permissionsPanelOpen = ref(false)
const permissionsPanelUserId = ref<string | null>(null)

const scopeKey = ref<string>('')

const scopeOptions = computed<PermissionScope[]>(() => manageableScopes.value)

function keyFor(scope: { scopeType: string, scopeId: string }): string {
  return `${scope.scopeType}:${scope.scopeId}`
}

const selectedScope = computed<PermissionScope | null>(() => {
  return scopeOptions.value.find(scope => keyFor(scope) === scopeKey.value) ?? scopeOptions.value[0] ?? null
})

function scopeLabel(scope: PermissionScope): string {
  const typeLabel = t(`governance.roles.scopeType.${scope.scopeType}`, scope.scopeType)
  return `${typeLabel} — ${scope.scopeId}`
}

async function load() {
  const scope = selectedScope.value
  if (!scope) {
    assignments.value = []
    loading.value = false
    return
  }

  loading.value = true
  try {
    assignments.value = await governanceApiService.listRoleAssignments(scope.scopeType, scope.scopeId)
  } catch (error) {
    handleError(error, { fallbackMessage: t('governance.roles.loadError', 'Nie udało się wczytać nadań ról') })
  } finally {
    loading.value = false
  }
}

watch(scopeOptions, (options) => {
  if (options.length > 0 && !options.some(scope => keyFor(scope) === scopeKey.value)) {
    scopeKey.value = keyFor(options[0])
  }
}, { immediate: true })

watch(selectedScope, () => {
  void load()
})

async function revoke(assignment: IRoleAssignment) {
  if (assignment.sourceAssignmentId) {
    toast.error(t('governance.roles.revokeFromServiceAssignment', 'Ta rola pochodzi z przypisania służby — usuń przypisanie zamiast tego'))
    return
  }
  if (!confirm(t('governance.roles.revokeConfirm', 'Czy na pewno chcesz odebrać tę rolę?'))) return

  revokingId.value = assignment.id
  try {
    await governanceApiService.deleteRoleAssignment(assignment.id)
    toast.success(t('governance.roles.revokeSuccess', 'Rola odebrana'))
    await load()
  } catch (error) {
    handleError(error, { fallbackMessage: t('governance.roles.revokeError', 'Nie udało się odebrać roli') })
  } finally {
    revokingId.value = null
  }
}

function roleLabel(roleName: string): string {
  return t(`congregations.people.roles.${roleName}`, roleName)
}

function openPermissionsPanel(assignment: IRoleAssignment) {
  permissionsPanelUserId.value = assignment.userId
  permissionsPanelOpen.value = true
}

const columns = computed<ColumnDef<IRoleAssignment>[]>(() => [
  {
    id: 'person',
    accessorKey: 'userId',
    header: () => t('governance.roles.columns.person', 'Osoba'),
  },
  {
    id: 'role',
    accessorKey: 'roleName',
    header: () => t('governance.roles.columns.role', 'Rola'),
  },
  {
    id: 'scope',
    accessorKey: 'scopeType',
    header: () => t('governance.roles.columns.scope', 'Zasięg'),
  },
  {
    id: 'source',
    accessorKey: 'sourceAssignmentId',
    header: () => t('governance.roles.columns.source', 'Źródło'),
  },
  {
    id: 'createdAt',
    accessorKey: 'createdAt',
    header: () => t('governance.roles.columns.createdAt', 'Nadano'),
  },
  {
    id: 'actions',
    header: () => t('governance.roles.columns.actions', 'Akcje'),
    enableSorting: false,
    meta: { pinned: 'right' },
  },
])

onMounted(load)
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="ShieldCheck"
        :label="t('governance.roles.title', 'Zarządzanie rolami')"
        :description="t('governance.roles.subtitle', 'Nadawaj i odbieraj role ACL we wspólnocie, rejonach, zborach i placówkach.')"
      />

      <div v-if="scopeOptions.length === 0" class="rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
        {{ t('governance.roles.noScopes', 'Nie zarządzasz jeszcze żadnym zasięgiem.') }}
      </div>

      <template v-else>
        <div class="max-w-sm space-y-1">
          <Select v-model="scopeKey">
            <SelectTrigger class="w-full">
              <SelectValue :placeholder="t('governance.roles.scopePlaceholder', 'Wybierz zasięg')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="scope in scopeOptions" :key="keyFor(scope)" :value="keyFor(scope)">
                {{ scopeLabel(scope) }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="flex justify-end">
          <Button type="button" @click="dialogOpen = true">
            {{ t('governance.roles.add', 'Nadaj rolę') }}
          </Button>
        </div>

        <DataTable
          :loading="loading"
          :columns="columns"
          :data="assignments"
          :enable-sorting="true"
          :enable-pagination="true"
          :initial-page-size="20"
        >
          <template #role="{ row }">
            {{ roleLabel(row.original.roleName) }}
          </template>

          <template #scope="{ row }">
            {{ t(`governance.roles.scopeType.${row.original.scopeType}`, row.original.scopeType) }}
          </template>

          <template #source="{ row }">
            <Badge :variant="row.original.sourceAssignmentId ? 'secondary' : 'outline'">
              {{ row.original.sourceAssignmentId
                ? t('governance.roles.source.service', 'Ze służby')
                : t('governance.roles.source.manual', 'Ręczne') }}
            </Badge>
          </template>

          <template #createdAt="{ row }">
            <span class="text-sm text-muted-foreground">
              {{ new Date(row.original.createdAt).toLocaleDateString() }}
            </span>
          </template>

          <template #actions="{ row }">
            <div class="flex justify-end gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                @click="openPermissionsPanel(row.original)"
              >
                {{ t('governance.permissions.title', 'Uprawnienia użytkownika') }}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="revokingId === row.original.id"
                @click="revoke(row.original)"
              >
                {{ t('governance.roles.revoke', 'Odbierz') }}
              </Button>
            </div>
          </template>
        </DataTable>

        <RoleAssignmentDialog
          v-if="selectedScope"
          v-model:open="dialogOpen"
          :scope-type="selectedScope.scopeType as GovernanceScopeType"
          :scope-id="selectedScope.scopeId"
          @granted="load"
        />

        <UserPermissionsPanel
          v-if="selectedScope && permissionsPanelUserId"
          v-model:open="permissionsPanelOpen"
          :user-id="permissionsPanelUserId"
          :scope-type="selectedScope.scopeType"
          :scope-id="selectedScope.scopeId"
        />

        <AclAuditSection
          v-if="selectedScope"
          :scope-type="selectedScope.scopeType"
          :scope-id="selectedScope.scopeId"
        />
      </template>
    </div>
  </AuthenticatedLayout>
</template>
