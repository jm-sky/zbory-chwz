<script setup lang="ts">
import { ArrowLeft, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import Card from '@/components/ui/card/Card.vue'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import PersonLinkedBadge from '@/shared/components/PersonLinkedBadge.vue'
import PersonSuggestionsList from '@/shared/components/PersonSuggestionsList.vue'
import { useHandleError } from '@/shared/composables/useHandleError'
import { usePermissions } from '@/shared/composables/usePermissions'
import { usePersonAutocomplete } from '@/shared/composables/usePersonAutocomplete'
import type { GroupVisibility, IGroupDetail, IGroupMembership } from '../types/group.types'
import { GroupsRoutePaths } from '../routes'
import { groupApiService } from '../services/groupApiService'

const { id } = defineProps<{ id: string }>()

const { t } = useI18n()
const router = useRouter()
const { canAccessAdminPanel, user } = usePermissions()
const { handleError } = useHandleError()

const group = ref<IGroupDetail | null>(null)
const loading = ref(true)

const editDialogOpen = ref(false)
const editForm = ref({ name: '', description: '', visibility: 'authenticated' as GroupVisibility })
const savingEdit = ref(false)

const memberForm = ref({ firstName: '', lastName: '', email: '', phone: '', roleLabel: '' })
const addingMember = ref(false)

const personAutocomplete = usePersonAutocomplete()

const canManageMetadata = canAccessAdminPanel

const canManageMembers = computed<boolean>(() => {
  if (canManageMetadata.value) return true
  return !!group.value?.stewardUserId && group.value.stewardUserId === user.value?.id
})

const activeMemberships = computed<IGroupMembership[]>(
  () => group.value?.memberships.filter(m => !m.leftAt) ?? [],
)

function personLabel(membership: IGroupMembership): string {
  const p = membership.person
  if (!p) return '—'
  const name = [p.firstName, p.lastName].filter(Boolean).join(' ')
  return name || p.email || '—'
}

function visibilityLabel(visibility: GroupVisibility): string {
  return t(`groups.visibility.${visibility}`, visibility)
}

async function load() {
  loading.value = true
  try {
    group.value = await groupApiService.getGroup(id)
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

function openEdit() {
  if (!group.value) return
  editForm.value = {
    name: group.value.name,
    description: group.value.description ?? '',
    visibility: group.value.visibility,
  }
  editDialogOpen.value = true
}

async function saveEdit() {
  if (!group.value) return
  savingEdit.value = true
  try {
    const updated = await groupApiService.updateGroup(group.value.id, {
      name: editForm.value.name,
      description: editForm.value.description || undefined,
      visibility: editForm.value.visibility,
    })
    group.value = { ...group.value, ...updated }
    editDialogOpen.value = false
    toast.success(t('groups.detail.updated', 'Zapisano zmiany'))
  } catch (error) {
    handleError(error)
  } finally {
    savingEdit.value = false
  }
}

async function deleteGroup() {
  if (!group.value) return
  if (!confirm(t('groups.detail.deleteConfirm', 'Usunąć tę grupę?'))) return
  try {
    await groupApiService.deleteGroup(group.value.id)
    toast.success(t('groups.detail.deleted', 'Grupa usunięta'))
    await router.push(GroupsRoutePaths.list)
  } catch (error) {
    handleError(error)
  }
}

function resetMemberForm() {
  memberForm.value = { firstName: '', lastName: '', email: '', phone: '', roleLabel: '' }
  personAutocomplete.reset()
}

function onMemberFieldChange(field: 'firstName' | 'lastName' | 'email' | 'phone', value: string) {
  personAutocomplete.handleFieldChange(field, value)
}

function onSelectPerson(person: Parameters<typeof personAutocomplete.selectPerson>[0]) {
  const filled = personAutocomplete.selectPerson(person)
  memberForm.value.firstName = filled.firstName
  memberForm.value.lastName = filled.lastName
  memberForm.value.email = filled.email
  memberForm.value.phone = filled.phone
}

async function addMember() {
  if (!group.value) return
  addingMember.value = true
  try {
    const membership = await groupApiService.addMembership(group.value.id, {
      personId: personAutocomplete.linkedPersonId.value ?? undefined,
      firstName: memberForm.value.firstName || undefined,
      lastName: memberForm.value.lastName || undefined,
      email: memberForm.value.email || undefined,
      phone: memberForm.value.phone || undefined,
      roleLabel: memberForm.value.roleLabel || undefined,
    })
    group.value.memberships.push(membership)
    group.value.memberCount += 1
    resetMemberForm()
    toast.success(t('groups.detail.memberAdded', 'Dodano członka'))
  } catch (error) {
    handleError(error)
  } finally {
    addingMember.value = false
  }
}

async function removeMember(membership: IGroupMembership) {
  if (!group.value) return
  if (!confirm(t('groups.detail.removeMemberConfirm', 'Usunąć tę osobę z grupy?'))) return
  try {
    await groupApiService.removeMembership(group.value.id, membership.id)
    const index = group.value.memberships.findIndex(m => m.id === membership.id)
    if (index >= 0) {
      group.value.memberships[index] = { ...membership, leftAt: new Date().toISOString() }
    }
    group.value.memberCount = Math.max(0, group.value.memberCount - 1)
    toast.success(t('groups.detail.memberRemoved', 'Usunięto z grupy'))
  } catch (error) {
    handleError(error)
  }
}

onMounted(load)
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <Button variant="ghost" size="sm" @click="router.push(GroupsRoutePaths.list)">
        <ArrowLeft class="size-4" />
        {{ t('groups.detail.back', 'Wróć do listy grup') }}
      </Button>

      <div v-if="loading" class="text-sm text-muted-foreground">
        {{ t('common.loading', 'Ładowanie...') }}
      </div>

      <template v-else-if="group">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="text-3xl font-bold tracking-tight flex items-center gap-3">
              {{ group.name }}
              <Badge variant="secondary">
                {{ visibilityLabel(group.visibility) }}
              </Badge>
            </h1>
            <p v-if="group.description" class="text-muted-foreground mt-2">
              {{ group.description }}
            </p>
          </div>
          <div v-if="canManageMetadata" class="flex gap-2 shrink-0">
            <Button
              type="button"
              variant="outline"
              size="icon"
              @click="openEdit"
            >
              <Pencil class="size-4" />
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              @click="deleteGroup"
            >
              <Trash2 class="size-4" />
            </Button>
          </div>
        </div>

        <Card class="p-4 space-y-4">
          <h3 class="text-lg font-semibold">
            {{ t('groups.detail.members', 'Członkowie') }}
          </h3>

          <ul class="space-y-2">
            <li
              v-for="membership in activeMemberships"
              :key="membership.id"
              class="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
            >
              <div>
                <p class="font-medium">
                  {{ personLabel(membership) }}
                </p>
                <p v-if="membership.roleLabel" class="text-sm text-muted-foreground">
                  {{ membership.roleLabel }}
                </p>
              </div>
              <Button
                v-if="canManageMembers"
                type="button"
                variant="ghost"
                size="icon"
                @click="removeMember(membership)"
              >
                <Trash2 class="size-4" />
              </Button>
            </li>
            <li v-if="activeMemberships.length === 0" class="text-sm text-muted-foreground">
              {{ t('groups.detail.noMembers', 'Brak członków') }}
            </li>
          </ul>

          <div v-if="canManageMembers" class="space-y-3 border-t pt-4">
            <PersonLinkedBadge
              v-if="personAutocomplete.linkedPersonId.value"
              @unlink="personAutocomplete.unlink()"
            />
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="relative space-y-1">
                <Label>{{ t('groups.fields.firstName', 'Imię') }}</Label>
                <Input
                  v-model="memberForm.firstName"
                  @update:model-value="onMemberFieldChange('firstName', String($event))"
                  @blur="personAutocomplete.closeSuggestions()"
                />
                <PersonSuggestionsList
                  v-if="personAutocomplete.activeField.value === 'firstName'"
                  :suggestions="personAutocomplete.suggestions.value"
                  @select="onSelectPerson"
                />
              </div>
              <div class="relative space-y-1">
                <Label>{{ t('groups.fields.lastName', 'Nazwisko') }}</Label>
                <Input
                  v-model="memberForm.lastName"
                  @update:model-value="onMemberFieldChange('lastName', String($event))"
                  @blur="personAutocomplete.closeSuggestions()"
                />
                <PersonSuggestionsList
                  v-if="personAutocomplete.activeField.value === 'lastName'"
                  :suggestions="personAutocomplete.suggestions.value"
                  @select="onSelectPerson"
                />
              </div>
              <div class="relative space-y-1">
                <Label>{{ t('groups.fields.email', 'E-mail') }}</Label>
                <Input
                  v-model="memberForm.email"
                  type="email"
                  @update:model-value="onMemberFieldChange('email', String($event))"
                  @blur="personAutocomplete.closeSuggestions()"
                />
                <PersonSuggestionsList
                  v-if="personAutocomplete.activeField.value === 'email'"
                  :suggestions="personAutocomplete.suggestions.value"
                  @select="onSelectPerson"
                />
              </div>
              <div class="relative space-y-1">
                <Label>{{ t('groups.fields.phone', 'Telefon') }}</Label>
                <Input
                  v-model="memberForm.phone"
                  @update:model-value="onMemberFieldChange('phone', String($event))"
                  @blur="personAutocomplete.closeSuggestions()"
                />
                <PersonSuggestionsList
                  v-if="personAutocomplete.activeField.value === 'phone'"
                  :suggestions="personAutocomplete.suggestions.value"
                  @select="onSelectPerson"
                />
              </div>
              <div class="space-y-1 sm:col-span-2">
                <Label>{{ t('groups.fields.roleLabel', 'Rola w grupie') }}</Label>
                <Input v-model="memberForm.roleLabel" :placeholder="t('groups.fields.roleLabelPlaceholder', 'np. Przewodniczący')" />
              </div>
            </div>
            <Button type="button" :disabled="addingMember" @click="addMember">
              <Plus class="size-4" />
              {{ t('groups.detail.addMember', 'Dodaj osobę') }}
            </Button>
          </div>
        </Card>
      </template>
    </div>

    <Dialog v-model:open="editDialogOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {{ t('groups.detail.editTitle', 'Edytuj grupę') }}
          </DialogTitle>
        </DialogHeader>

        <div class="space-y-3">
          <div class="space-y-1">
            <Label>{{ t('groups.fields.name', 'Nazwa') }}</Label>
            <Input v-model="editForm.name" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('groups.fields.description', 'Opis') }}</Label>
            <Textarea v-model="editForm.description" rows="2" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('groups.fields.visibility', 'Widoczność') }}</Label>
            <Select v-model="editForm.visibility">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent class="z-[100]">
                <SelectItem value="public">
                  {{ t('groups.visibility.public', 'Publiczna') }}
                </SelectItem>
                <SelectItem value="authenticated">
                  {{ t('groups.visibility.authenticated', 'Zalogowani') }}
                </SelectItem>
                <SelectItem value="private">
                  {{ t('groups.visibility.private', 'Prywatna') }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" @click="editDialogOpen = false">
            {{ t('common.cancel', 'Anuluj') }}
          </Button>
          <Button type="button" :disabled="savingEdit" @click="saveEdit">
            {{ t('common.save', 'Zapisz') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AuthenticatedLayout>
</template>
