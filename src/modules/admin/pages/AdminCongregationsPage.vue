<script setup lang="ts">
import { Church, EyeOff, Globe, MoreHorizontal, Plus, Trash2, Users } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import DataTable from '@/components/data-table/DataTable.vue'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import TableEmptyDecorated from '@/components/ui/table/TableEmptyDecorated.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IAdminUser } from '../types/admin.types'
import type { IAddress, IAdminTenant, IAdminTenantMembership } from '../types/tenant.types'
import { adminApiService } from '../services/adminApiService'
import type { ColumnDef } from '@tanstack/vue-table'

const { t } = useI18n()
const { handleError } = useHandleError()
const tenants = ref<IAdminTenant[]>([])
const loading = ref(false)
const createDialogOpen = ref(false)
const editDialogOpen = ref(false)
const membershipsDialogOpen = ref(false)
const selectedTenant = ref<IAdminTenant | null>(null)
const memberships = ref<IAdminTenantMembership[]>([])
const allUsers = ref<IAdminUser[]>([])
const loadingMemberships = ref(false)
const loadingAddress = ref(false)
const currentAddress = ref<IAddress | null>(null)

const formData = ref({
  name: '',
  description: '',
  status: 'draft',
  address: {
    street: '',
    city: '',
    postal_code: '',
  },
})

const membershipFormData = ref({
  user_id: '',
  role: 'member',
})

// Load tenants
async function loadTenants() {
  loading.value = true
  try {
    tenants.value = await adminApiService.getTenants()
  } catch (error) {
    console.error('Failed to load tenants:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.loadError', 'Failed to load congregations') })
  } finally {
    loading.value = false
  }
}

// Create tenant
async function createTenant() {
  if (!formData.value.name.trim()) {
    toast.error(t('admin.congregations.nameRequired', 'Name is required'))
    return
  }

  try {
    await adminApiService.createTenant({
      name: formData.value.name.trim(),
      description: formData.value.description.trim() || undefined,
      status: formData.value.status,
    })
    toast.success(t('admin.congregations.createSuccess', 'Congregation created successfully'))
    createDialogOpen.value = false
    resetForm()
    await loadTenants()
  } catch (error) {
    console.error('Failed to create tenant:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.createError', 'Failed to create congregation') })
  }
}

// Update tenant
async function updateTenant() {
  if (!selectedTenant.value) return
  if (!formData.value.name.trim()) {
    toast.error(t('admin.congregations.nameRequired', 'Name is required'))
    return
  }

  try {
    await adminApiService.updateTenant(selectedTenant.value.id, {
      name: formData.value.name.trim(),
      description: formData.value.description.trim() || undefined,
      status: formData.value.status,
    })
    
    // Update address
    if (formData.value.address.city.trim()) {
      if (currentAddress.value) {
        await adminApiService.updateAddress(selectedTenant.value.id, {
          street: formData.value.address.street.trim() || null,
          city: formData.value.address.city.trim(),
          postal_code: formData.value.address.postal_code.trim() || null,
          status: formData.value.status,
        })
      } else {
        await adminApiService.createOrUpdateAddress(selectedTenant.value.id, {
          street: formData.value.address.street.trim() || null,
          city: formData.value.address.city.trim(),
          postal_code: formData.value.address.postal_code.trim() || null,
          country: 'Poland',
          status: formData.value.status,
        })
      }
    } else if (currentAddress.value) {
      // Update address status even if city is not provided
      await adminApiService.updateAddress(selectedTenant.value.id, {
        status: formData.value.status,
      })
    }
    
    toast.success(t('admin.congregations.updateSuccess', 'Congregation updated successfully'))
    editDialogOpen.value = false
    selectedTenant.value = null
    resetForm()
    await loadTenants()
  } catch (error) {
    console.error('Failed to update tenant:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.updateError', 'Failed to update congregation') })
  }
}

// Publish tenant
async function publishTenant(tenant: IAdminTenant) {
  try {
    await adminApiService.updateTenant(tenant.id, {
      status: 'published',
    })
    toast.success(t('admin.congregations.publishSuccess', 'Congregation published successfully'))
    await loadTenants()
  } catch (error) {
    console.error('Failed to publish tenant:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.publishError', 'Failed to publish congregation') })
  }
}

// Unpublish tenant
async function unpublishTenant(tenant: IAdminTenant) {
  try {
    await adminApiService.updateTenant(tenant.id, {
      status: 'draft',
    })
    toast.success(t('admin.congregations.unpublishSuccess', 'Congregation unpublished successfully'))
    await loadTenants()
  } catch (error) {
    console.error('Failed to unpublish tenant:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.unpublishError', 'Failed to unpublish congregation') })
  }
}

// Delete tenant
async function deleteTenant(tenantId: string) {
  if (!confirm(t('admin.congregations.deleteConfirm', 'Are you sure you want to delete this congregation?'))) {
    return
  }

  try {
    await adminApiService.deleteTenant(tenantId)
    toast.success(t('admin.congregations.deleteSuccess', 'Congregation deleted successfully'))
    await loadTenants()
  } catch (error) {
    console.error('Failed to delete tenant:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.deleteError', 'Failed to delete congregation') })
  }
}

// Open edit dialog
async function openEditDialog(tenant: IAdminTenant) {
  selectedTenant.value = tenant
  formData.value = {
    name: tenant.name,
    description: tenant.description || '',
    status: tenant.status || 'draft',
    address: {
      street: '',
      city: '',
      postal_code: '',
    },
  }
  editDialogOpen.value = true
  
  // Load address
  loadingAddress.value = true
  try {
    currentAddress.value = await adminApiService.getAddress(tenant.id)
    if (currentAddress.value) {
      formData.value.address = {
        street: currentAddress.value.street || '',
        city: currentAddress.value.city || '',
        postal_code: currentAddress.value.postal_code || '',
      }
    }
  } catch (error) {
    // 404 is handled in service (returns null), only log other errors
    handleError(error, { fallbackMessage: t('admin.congregations.address.loadError', 'Failed to load address') })
  } finally {
    loadingAddress.value = false
  }
}

// Open memberships dialog
async function openMembershipsDialog(tenant: IAdminTenant) {
  selectedTenant.value = tenant
  membershipsDialogOpen.value = true
  await loadMemberships(tenant.id)
  await loadAllUsers()
}

// Load memberships
async function loadMemberships(tenantId: string) {
  loadingMemberships.value = true
  try {
    memberships.value = await adminApiService.getTenantMemberships(tenantId)
  } catch (error) {
    console.error('Failed to load memberships:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.memberships.loadError', 'Failed to load members') })
  } finally {
    loadingMemberships.value = false
  }
}

// Load all users for membership assignment
async function loadAllUsers() {
  try {
    allUsers.value = await adminApiService.getUsers(0, 1000)
  } catch (error) {
    console.error('Failed to load users:', error)
  }
}

// Create membership
async function createMembership() {
  if (!selectedTenant.value) return
  if (!membershipFormData.value.user_id) {
    toast.error(t('admin.congregations.memberships.userRequired', 'User is required'))
    return
  }

  try {
    await adminApiService.createTenantMembership(selectedTenant.value.id, {
      user_id: membershipFormData.value.user_id,
      role: membershipFormData.value.role,
    })
    toast.success(t('admin.congregations.memberships.createSuccess', 'Member added successfully'))
    resetMembershipForm()
    await loadMemberships(selectedTenant.value.id)
  } catch (error) {
    console.error('Failed to create membership:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.memberships.createError', 'Failed to add member') })
  }
}

// Update membership
async function updateMembership(membership: IAdminTenantMembership, newRole: string | null) {
  if (!selectedTenant.value) return
  if (!newRole) return

  try {
    await adminApiService.updateTenantMembership(selectedTenant.value.id, membership.user_id, {
      role: newRole,
    })
    toast.success(t('admin.congregations.memberships.updateSuccess', 'Member role updated successfully'))
    await loadMemberships(selectedTenant.value.id)
  } catch (error) {
    console.error('Failed to update membership:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.memberships.updateError', 'Failed to update member role') })
  }
}

// Delete membership
async function deleteMembership(membership: IAdminTenantMembership) {
  if (!selectedTenant.value) return
  if (!confirm(t('admin.congregations.memberships.deleteConfirm', 'Are you sure you want to remove this member?'))) {
    return
  }

  try {
    await adminApiService.deleteTenantMembership(selectedTenant.value.id, membership.user_id)
    toast.success(t('admin.congregations.memberships.deleteSuccess', 'Member removed successfully'))
    await loadMemberships(selectedTenant.value.id)
  } catch (error) {
    console.error('Failed to delete membership:', error)
    handleError(error, { fallbackMessage: t('admin.congregations.memberships.deleteError', 'Failed to remove member') })
  }
}

function resetForm() {
  formData.value = {
    name: '',
    description: '',
    status: 'draft',
    address: {
      street: '',
      city: '',
      postal_code: '',
    },
  }
  selectedTenant.value = null
  currentAddress.value = null
}

function resetMembershipForm() {
  membershipFormData.value = {
    user_id: '',
    role: 'member',
  }
}

// Get available users (not already members)
const availableUsers = computed(() => {
  const memberUserIds = new Set(memberships.value.map(m => m.user_id))
  return allUsers.value.filter(user => !memberUserIds.has(user.id))
})

// Columns
const columns = computed<ColumnDef<IAdminTenant>[]>(() => [
  {
    id: 'name',
    accessorKey: 'name',
    header: () => t('admin.congregations.columns.name', 'Name'),
    enableSorting: true,
  },
  {
    id: 'description',
    accessorKey: 'description',
    header: () => t('admin.congregations.columns.description', 'Description'),
    enableSorting: false,
  },
  {
    id: 'status',
    accessorKey: 'status',
    header: () => t('admin.congregations.columns.status', 'Status'),
    enableSorting: true,
  },
  {
    id: 'createdAt',
    accessorKey: 'createdAt',
    header: () => t('admin.congregations.columns.createdAt', 'Created'),
    enableSorting: true,
  },
  {
    id: 'actions',
    header: () => t('admin.congregations.columns.actions', 'Actions'),
    enableSorting: false,
    meta: {
      pinned: 'right',
    },
  },
])

// Global filter function
const globalFilterFn = (row: IAdminTenant, filterValue: string) => {
  const query = filterValue.toLowerCase()
  return (
    row.name.toLowerCase().includes(query) ||
    (row.description?.toLowerCase().includes(query) ?? false)
  )
}

onMounted(() => {
  loadTenants()
})
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <!-- Header -->
      <CommonPageHeader
        :icon="Church"
        :label="t('admin.congregations.title', 'Congregations Management')"
        :description="t('admin.congregations.subtitle', 'Manage congregations (tenants) and their members')"
      >
        <Dialog v-model:open="createDialogOpen">
          <DialogTrigger as-child>
            <Button>
              <Plus class="size-4" />
              {{ t('admin.congregations.create', 'Create Congregation') }}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {{ t('admin.congregations.createTitle', 'Create New Congregation') }}
              </DialogTitle>
              <DialogDescription>
                {{ t('admin.congregations.createDescription', 'Add a new congregation to the system') }}
              </DialogDescription>
            </DialogHeader>
            <div class="space-y-4 py-4">
              <div class="space-y-2">
                <Label for="create-name">
                  {{ t('admin.congregations.name', 'Name') }} *
                </Label>
                <Input
                  id="create-name"
                  v-model="formData.name"
                  :placeholder="t('admin.congregations.namePlaceholder', 'Enter congregation name')"
                />
              </div>
              <div class="space-y-2">
                <Label for="create-description">
                  {{ t('admin.congregations.description', 'Description') }}
                </Label>
                <Input
                  id="create-description"
                  v-model="formData.description"
                  :placeholder="t('admin.congregations.descriptionPlaceholder', 'Enter description (optional)')"
                />
              </div>
              <div class="space-y-2">
                <Label for="create-status">
                  {{ t('admin.congregations.status', 'Status') }}
                </Label>
                <Select v-model="formData.status">
                  <SelectTrigger id="create-status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">
                      {{ t('admin.congregations.statusDraft', 'Draft') }}
                    </SelectItem>
                    <SelectItem value="published">
                      {{ t('admin.congregations.statusPublished', 'Published') }}
                    </SelectItem>
                    <SelectItem value="published_unverified">
                      {{ t('admin.congregations.statusPublishedUnverified', 'Published (Unverified)') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" @click="createDialogOpen = false">
                {{ t('common.cancel', 'Cancel') }}
              </Button>
              <Button @click="createTenant">
                {{ t('common.create', 'Create') }}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CommonPageHeader>

      <!-- Edit Dialog -->
      <Dialog v-model:open="editDialogOpen">
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {{ t('admin.congregations.editTitle', 'Edit Congregation') }}
            </DialogTitle>
            <DialogDescription>
              {{ t('admin.congregations.editDescription', 'Update congregation information') }}
            </DialogDescription>
          </DialogHeader>
          <div class="space-y-4 py-4">
            <div class="space-y-2">
              <Label for="edit-name">
                {{ t('admin.congregations.name', 'Name') }} *
              </Label>
              <Input
                id="edit-name"
                v-model="formData.name"
                :placeholder="t('admin.congregations.namePlaceholder', 'Enter congregation name')"
              />
            </div>
            <div class="space-y-2">
              <Label for="edit-description">
                {{ t('admin.congregations.description', 'Description') }}
              </Label>
              <Input
                id="edit-description"
                v-model="formData.description"
                :placeholder="t('admin.congregations.descriptionPlaceholder', 'Enter description (optional)')"
              />
            </div>
            <div class="space-y-2">
              <Label for="edit-status">
                {{ t('admin.congregations.status', 'Status') }}
              </Label>
              <Select v-model="formData.status">
                <SelectTrigger id="edit-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">
                    {{ t('admin.congregations.statusDraft', 'Draft') }}
                  </SelectItem>
                  <SelectItem value="published">
                    {{ t('admin.congregations.statusPublished', 'Published') }}
                  </SelectItem>
                  <SelectItem value="published_unverified">
                    {{ t('admin.congregations.statusPublishedUnverified', 'Published (Unverified)') }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <!-- Address Section -->
            <div class="space-y-4 pt-4 border-t">
              <h4 class="font-semibold text-sm">
                {{ t('admin.congregations.address.title', 'Address') }}
              </h4>
              <div v-if="loadingAddress" class="text-sm text-muted-foreground">
                {{ t('admin.congregations.address.loading', 'Loading address...') }}
              </div>
              <div v-else class="space-y-4">
                <div class="space-y-2">
                  <Label for="edit-address-street">
                    {{ t('admin.congregations.address.street', 'Street') }}
                  </Label>
                  <Input
                    id="edit-address-street"
                    v-model="formData.address.street"
                    :placeholder="t('admin.congregations.address.streetPlaceholder', 'Enter street address')"
                  />
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-2">
                    <Label for="edit-address-city">
                      {{ t('admin.congregations.address.city', 'City') }}
                    </Label>
                    <Input
                      id="edit-address-city"
                      v-model="formData.address.city"
                      :placeholder="t('admin.congregations.address.cityPlaceholder', 'Enter city')"
                    />
                  </div>
                  <div class="space-y-2">
                    <Label for="edit-address-postal-code">
                      {{ t('admin.congregations.address.postalCode', 'Postal Code') }}
                    </Label>
                    <Input
                      id="edit-address-postal-code"
                      v-model="formData.address.postal_code"
                      :placeholder="t('admin.congregations.address.postalCodePlaceholder', 'Enter postal code')"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" @click="editDialogOpen = false">
              {{ t('common.cancel', 'Cancel') }}
            </Button>
            <Button @click="updateTenant">
              {{ t('common.save', 'Save') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- Memberships Dialog -->
      <Dialog v-model:open="membershipsDialogOpen">
        <DialogContent class="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {{ t('admin.congregations.memberships.title', 'Manage Members') }} - {{ selectedTenant?.name }}
            </DialogTitle>
            <DialogDescription>
              {{ t('admin.congregations.memberships.description', 'Add, edit, or remove members from this congregation') }}
            </DialogDescription>
          </DialogHeader>
          <div class="space-y-4 py-4">
            <!-- Add Member Form -->
            <div class="rounded-lg border p-4 space-y-3">
              <h4 class="font-semibold text-sm">
                {{ t('admin.congregations.memberships.addMember', 'Add Member') }}
              </h4>
              <div class="grid grid-cols-2 gap-3">
                <div class="space-y-2">
                  <Label for="membership-user">
                    {{ t('admin.congregations.memberships.user', 'User') }} *
                  </Label>
                  <Select v-model="membershipFormData.user_id">
                    <SelectTrigger id="membership-user">
                      <SelectValue :placeholder="t('admin.congregations.memberships.selectUser', 'Select user')" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem
                        v-for="user in availableUsers"
                        :key="user.id"
                        :value="user.id"
                      >
                        {{ user.name }} ({{ user.email }})
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div class="space-y-2">
                  <Label for="membership-role">
                    {{ t('admin.congregations.memberships.role', 'Role') }}
                  </Label>
                  <Select v-model="membershipFormData.role">
                    <SelectTrigger id="membership-role">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">
                        {{ t('admin.congregations.memberships.roleMember', 'Member') }}
                      </SelectItem>
                      <SelectItem value="owner">
                        {{ t('admin.congregations.memberships.roleOwner', 'Owner') }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button
                :disabled="!membershipFormData.user_id"
                @click="createMembership"
              >
                <Plus class="size-4" />
                {{ t('admin.congregations.memberships.add', 'Add Member') }}
              </Button>
            </div>

            <!-- Members List -->
            <div class="space-y-2">
              <h4 class="font-semibold text-sm">
                {{ t('admin.congregations.memberships.members', 'Members') }} ({{ memberships.length }})
              </h4>
              <div v-if="loadingMemberships" class="space-y-2">
                <div
                  v-for="i in 3"
                  :key="i"
                  class="h-16 animate-pulse rounded-lg bg-muted"
                />
              </div>
              <div v-else-if="memberships.length === 0" class="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
                <Users class="mx-auto mb-2 size-8 opacity-50" />
                <p>{{ t('admin.congregations.memberships.empty', 'No members yet') }}</p>
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="membership in memberships"
                  :key="`${membership.tenant_id}-${membership.user_id}`"
                  class="flex items-center justify-between rounded-lg border p-3"
                >
                  <div class="flex-1">
                    <p class="font-medium">
                      {{ membership.user_name || membership.user_email || membership.user_id }}
                    </p>
                    <p class="text-sm text-muted-foreground">
                      {{ membership.user_email }}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <Select
                      :model-value="membership.role"
                      @update:model-value="(value) => updateMembership(membership, typeof value === 'string' ? value : null)"
                    >
                      <SelectTrigger class="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="member">
                          {{ t('admin.congregations.memberships.roleMember', 'Member') }}
                        </SelectItem>
                        <SelectItem value="owner">
                          {{ t('admin.congregations.memberships.roleOwner', 'Owner') }}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="deleteMembership(membership)"
                    >
                      <Trash2 class="size-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" @click="membershipsDialogOpen = false">
              {{ t('common.close', 'Close') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- Table -->
      <DataTable
        :loading="loading"
        :columns="columns"
        :data="tenants"
        :search-placeholder="t('admin.congregations.search', 'Search congregations...')"
        :global-filter-fn="globalFilterFn"
        :enable-sorting="true"
        :enable-filtering="true"
        :enable-pagination="true"
        :initial-page-size="20"
      >
        <template #name="{ row }">
          <div class="flex items-center gap-2">
            <div class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Church class="size-4 text-primary" />
            </div>
            <span class="font-medium">{{ row.original.name }}</span>
          </div>
        </template>

        <template #description="{ row }">
          <span class="text-muted-foreground line-clamp-1">
            {{ row.original.description || '-' }}
          </span>
        </template>

        <template #status="{ row }">
          <Badge v-if="row.original.status === 'published'" variant="default">
            {{ t('admin.congregations.statusPublished', 'Published') }}
          </Badge>
          <Badge v-else-if="row.original.status === 'published_unverified'" variant="outline" class="opacity-60">
            {{ t('admin.congregations.statusPublishedUnverified', 'Published (Unverified)') }}
          </Badge>
          <Badge v-else variant="secondary">
            {{ t('admin.congregations.statusDraft', 'Draft') }}
          </Badge>
        </template>

        <template #createdAt="{ row }">
          <span class="text-sm text-muted-foreground">
            {{ new Date(row.original.createdAt).toLocaleDateString() }}
          </span>
        </template>

        <template #actions="{ row }">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="sm">
                <MoreHorizontal class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="openEditDialog(row.original)">
                {{ t('common.edit', 'Edit') }}
              </DropdownMenuItem>
              <DropdownMenuItem @click="openMembershipsDialog(row.original)">
                <Users class="size-4" />
                <span>{{ t('admin.congregations.manageMembers', 'Manage Members') }}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                v-if="row.original.status !== 'published' && row.original.status !== 'published_unverified'"
                @click="publishTenant(row.original)"
              >
                <Globe class="size-4" />
                <span>{{ t('admin.congregations.publish', 'Publish') }}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                v-if="row.original.status === 'published' || row.original.status === 'published_unverified'"
                @click="unpublishTenant(row.original)"
              >
                <EyeOff class="size-4" />
                <span>{{ t('admin.congregations.unpublish', 'Unpublish') }}</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                class="text-destructive focus:text-destructive"
                @click="deleteTenant(row.original.id)"
              >
                <Trash2 class="size-4" />
                <span>{{ t('common.delete', 'Delete') }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </template>

        <template #empty>
          <TableEmptyDecorated
            :colspan="columns.length"
            :title="t('admin.congregations.empty', 'No congregations found')"
            :description="t('admin.congregations.emptyDescription', 'No congregations match your search criteria.')"
          />
        </template>
      </DataTable>
    </div>
  </AuthenticatedLayout>
</template>
