<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Button from '@/components/ui/button/Button.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useHandleError } from '@/shared/composables/useHandleError'
import type { IBranch } from '../types/church.types'
import { churchApiService } from '../services/churchApiService'

const { churchId } = defineProps<{ churchId: string }>()

const { t } = useI18n()
const { handleError } = useHandleError()

const branches = ref<IBranch[]>([])
const loading = ref(true)
const newName = ref('')

async function loadBranches() {
  loading.value = true
  try {
    branches.value = await churchApiService.listBranches(churchId)
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

async function addBranch() {
  if (!newName.value.trim()) return
  try {
    const branch = await churchApiService.createBranch(churchId, { name: newName.value.trim() })
    branches.value.push(branch)
    newName.value = ''
    toast.success(t('congregations.branches.added', 'Placówka dodana'))
  } catch (error) {
    handleError(error)
  }
}

async function removeBranch(branchId: string) {
  try {
    await churchApiService.deleteBranch(churchId, branchId)
    branches.value = branches.value.filter(b => b.id !== branchId)
    toast.success(t('congregations.branches.removed', 'Placówka usunięta'))
  } catch (error) {
    handleError(error)
  }
}

onMounted(loadBranches)
</script>

<template>
  <div class="space-y-4 rounded-lg border p-4">
    <h3 class="text-lg font-semibold">
      {{ t('congregations.branches.title', 'Placówki') }}
    </h3>

    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="branch in branches"
        :key="branch.id"
        class="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
      >
        <span>{{ branch.name }}</span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          @click="removeBranch(branch.id)"
        >
          <Trash2 class="size-4" />
        </Button>
      </li>
      <li v-if="branches.length === 0" class="text-sm text-muted-foreground">
        {{ t('congregations.branches.empty', 'Brak placówek') }}
      </li>
    </ul>

    <div class="flex flex-col gap-2 sm:flex-row sm:items-end">
      <div class="grow space-y-1">
        <Label for="branch-name">{{ t('congregations.branches.name', 'Nazwa placówki') }}</Label>
        <Input
          id="branch-name"
          v-model="newName"
          :placeholder="t('congregations.branches.namePlaceholder', 'np. Placówka Praga')"
        />
      </div>
      <Button type="button" @click="addBranch">
        <Plus class="size-4" />
        {{ t('congregations.branches.add', 'Dodaj') }}
      </Button>
    </div>
  </div>
</template>
