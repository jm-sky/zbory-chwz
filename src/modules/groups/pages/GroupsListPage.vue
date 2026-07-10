<script setup lang="ts">
import { Plus, Users } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
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
import { useHandleError } from '@/shared/composables/useHandleError'
import { usePermissions } from '@/shared/composables/usePermissions'
import type { GroupVisibility, IGroup } from '../types/group.types'
import { GroupsRoutePaths } from '../routes'
import { groupApiService } from '../services/groupApiService'

const { t } = useI18n()
const { canAccessAdminPanel } = usePermissions()
const { handleError } = useHandleError()

const groups = ref<IGroup[]>([])
const loading = ref(true)
const createDialogOpen = ref(false)
const creating = ref(false)

const form = ref({
  name: '',
  description: '',
  visibility: 'authenticated' as GroupVisibility,
})

const canManageGroups = canAccessAdminPanel

function visibilityLabel(visibility: GroupVisibility): string {
  return t(`groups.visibility.${visibility}`, visibility)
}

async function load() {
  loading.value = true
  try {
    groups.value = await groupApiService.listGroups()
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = { name: '', description: '', visibility: 'authenticated' }
}

async function createGroup() {
  if (!form.value.name.trim()) return
  creating.value = true
  try {
    const created = await groupApiService.createGroup({
      name: form.value.name,
      description: form.value.description || undefined,
      visibility: form.value.visibility,
    })
    groups.value.push(created)
    createDialogOpen.value = false
    resetForm()
    toast.success(t('groups.list.created', 'Grupa utworzona'))
  } catch (error) {
    handleError(error)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Users class="size-8 text-primary" />
            {{ t('groups.list.title', 'Grupy ludzi') }}
          </h1>
          <p class="text-muted-foreground mt-2">
            {{ t('groups.list.subtitle', 'Struktury organizacyjne niezależne od pojedynczego zboru') }}
          </p>
        </div>
        <Button v-if="canManageGroups" type="button" @click="createDialogOpen = true">
          <Plus class="size-4" />
          {{ t('groups.list.create', 'Nowa grupa') }}
        </Button>
      </div>

      <div v-if="loading" class="text-sm text-muted-foreground">
        {{ t('common.loading', 'Ładowanie...') }}
      </div>

      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="group in groups"
          :key="group.id"
          :to="GroupsRoutePaths.detailById(group.id)"
        >
          <Card class="p-4 h-full hover:border-primary transition-colors">
            <div class="flex items-start justify-between gap-2">
              <h3 class="font-semibold">
                {{ group.name }}
              </h3>
              <Badge variant="secondary">
                {{ visibilityLabel(group.visibility) }}
              </Badge>
            </div>
            <p v-if="group.description" class="text-sm text-muted-foreground mt-1 line-clamp-2">
              {{ group.description }}
            </p>
            <p class="text-sm text-muted-foreground mt-2">
              {{ t('groups.list.memberCount', { count: group.memberCount }) }}
            </p>
          </Card>
        </RouterLink>

        <p v-if="groups.length === 0" class="text-sm text-muted-foreground">
          {{ t('groups.list.empty', 'Brak grup') }}
        </p>
      </div>
    </div>

    <Dialog v-model:open="createDialogOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {{ t('groups.list.createTitle', 'Nowa grupa') }}
          </DialogTitle>
        </DialogHeader>

        <div class="space-y-3">
          <div class="space-y-1">
            <Label>{{ t('groups.fields.name', 'Nazwa') }}</Label>
            <Input v-model="form.name" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('groups.fields.description', 'Opis') }}</Label>
            <Textarea v-model="form.description" rows="2" />
          </div>
          <div class="space-y-1">
            <Label>{{ t('groups.fields.visibility', 'Widoczność') }}</Label>
            <Select v-model="form.visibility">
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
          <Button type="button" variant="outline" @click="createDialogOpen = false">
            {{ t('common.cancel', 'Anuluj') }}
          </Button>
          <Button type="button" :disabled="creating || !form.name.trim()" @click="createGroup">
            {{ t('common.save', 'Zapisz') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AuthenticatedLayout>
</template>
