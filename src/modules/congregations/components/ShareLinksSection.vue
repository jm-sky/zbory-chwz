<script setup lang="ts">
import { useClipboard } from '@vueuse/core'
import { Copy, Link2, Trash2 } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Badge } from '@/components/ui/badge'
import Button from '@/components/ui/button/Button.vue'
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
import { useHandleError } from '@/shared/composables/useHandleError'
import type { ShareableVisibilityLevel, ShareLinkExpiryDays } from '../types/shareLink.types'
import { useCreateShareLink, useRevokeShareLink, useShareLinks } from '../composables/useShareLinks'
import VisibilityLevelSelect from './VisibilityLevelSelect.vue'

const { tenantId = null } = defineProps<{ tenantId?: string | null }>()

const { t } = useI18n()
const { handleError } = useHandleError()
const { copy } = useClipboard()

const { data: shareLinks, isLoading } = useShareLinks(tenantId)
const createShareLink = useCreateShareLink(tenantId)
const revokeShareLink = useRevokeShareLink(tenantId)

const EXPIRY_OPTIONS: ShareLinkExpiryDays[] = [3, 7, 14, 30]

const createDialogOpen = ref(false)
const form = ref<{ visibilityLevel: ShareableVisibilityLevel; expiresInDays: string; label: string }>({
  visibilityLevel: 'authenticated',
  expiresInDays: '7',
  label: '',
})
const createdLink = ref<string | null>(null)

function shareUrl(token: string): string {
  return `${window.location.origin}/share/${token}`
}

function openCreateDialog(): void {
  form.value = { visibilityLevel: 'authenticated', expiresInDays: '7', label: '' }
  createdLink.value = null
  createDialogOpen.value = true
}

async function handleCreate(): Promise<void> {
  try {
    const link = await createShareLink.mutateAsync({
      visibility_level: form.value.visibilityLevel,
      expires_in_days: Number(form.value.expiresInDays) as ShareLinkExpiryDays,
      label: form.value.label.trim() || undefined,
    })
    createdLink.value = shareUrl(link.token)
  } catch (error) {
    handleError(error, { fallbackMessage: t('congregations.share.createError') })
  }
}

async function handleCopy(url: string): Promise<void> {
  await copy(url)
  toast.success(t('congregations.share.copySuccess'))
}

async function handleRevoke(linkId: string): Promise<void> {
  if (!confirm(t('congregations.share.revokeConfirm'))) return

  try {
    await revokeShareLink.mutateAsync(linkId)
    toast.success(t('congregations.share.revokeSuccess'))
  } catch (error) {
    handleError(error, { fallbackMessage: t('congregations.share.revokeError') })
  }
}

function formatExpiresAt(value: string): string {
  return new Date(value).toLocaleDateString()
}

const visibilityLabel = computed(() => (level: ShareableVisibilityLevel) =>
  t(`congregations.people.visibility.${level}`),
)
</script>

<template>
  <div class="space-y-4 rounded-lg border p-4">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h3 class="text-lg font-semibold">
          {{ tenantId ? t('congregations.share.title') : t('congregations.share.globalTitle') }}
        </h3>
        <p v-if="!tenantId" class="text-sm text-muted-foreground">
          {{ t('congregations.share.globalDescription') }}
        </p>
      </div>
      <Button size="sm" @click="openCreateDialog">
        <Link2 class="size-4" />
        {{ t('congregations.share.create') }}
      </Button>
    </div>

    <div v-if="isLoading" class="text-sm text-muted-foreground">
      {{ t('common.loading', 'Ładowanie...') }}
    </div>
    <p v-else-if="!shareLinks || shareLinks.length === 0" class="text-sm text-muted-foreground">
      {{ t('congregations.share.empty') }}
    </p>

    <ul v-else class="space-y-2">
      <li
        v-for="link in shareLinks"
        :key="link.id"
        class="flex flex-col gap-2 rounded-md border px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span v-if="link.label" class="font-medium">{{ link.label }}</span>
            <Badge variant="outline">
              {{ visibilityLabel(link.visibility_level) }}
            </Badge>
          </div>
          <p class="text-xs text-muted-foreground">
            {{ t('congregations.share.expiresAt', { date: formatExpiresAt(link.expires_at) }) }}
          </p>
        </div>
        <div class="flex items-center gap-2 self-end sm:self-auto">
          <Button
            variant="outline"
            size="icon"
            :aria-label="t('congregations.share.copyLink')"
            @click="handleCopy(shareUrl(link.token))"
          >
            <Copy class="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            class="text-destructive hover:text-destructive"
            :aria-label="t('congregations.share.revoke')"
            @click="handleRevoke(link.id)"
          >
            <Trash2 class="size-4" />
          </Button>
        </div>
      </li>
    </ul>

    <Dialog v-model:open="createDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('congregations.share.createTitle') }}</DialogTitle>
        </DialogHeader>

        <template v-if="createdLink">
          <div class="space-y-2">
            <Label>{{ t('congregations.share.generatedLink') }}</Label>
            <div class="flex gap-2">
              <Input :model-value="createdLink" readonly class="flex-1" />
              <Button variant="outline" @click="handleCopy(createdLink)">
                <Copy class="size-4" />
              </Button>
            </div>
          </div>
        </template>

        <div v-else class="space-y-4 py-2">
          <VisibilityLevelSelect
            v-model="form.visibilityLevel"
            :label="t('congregations.share.visibilityLevel')"
            :levels="['authenticated', 'pastors']"
          />
          <p class="text-xs text-muted-foreground">
            {{ t('congregations.share.readOnlyNote') }}
          </p>

          <div class="space-y-1">
            <Label>{{ t('congregations.share.expiresIn') }}</Label>
            <Select v-model="form.expiresInDays">
              <SelectTrigger class="max-w-md">
                <SelectValue />
              </SelectTrigger>
              <SelectContent class="z-[100]">
                <SelectItem
                  v-for="days in EXPIRY_OPTIONS"
                  :key="days"
                  :value="String(days)"
                >
                  {{ t('congregations.share.expiresInDays', { count: days }, days) }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-1">
            <Label for="share-link-label">{{ t('congregations.share.label') }}</Label>
            <Input
              id="share-link-label"
              v-model="form.label"
              :placeholder="t('congregations.share.labelPlaceholder')"
            />
          </div>
        </div>

        <DialogFooter>
          <Button v-if="!createdLink" variant="outline" @click="createDialogOpen = false">
            {{ t('common.cancel', 'Anuluj') }}
          </Button>
          <Button v-if="!createdLink" :disabled="createShareLink.isPending.value" @click="handleCreate">
            {{ t('congregations.share.create') }}
          </Button>
          <Button v-else @click="createDialogOpen = false">
            {{ t('common.close', 'Zamknij') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
