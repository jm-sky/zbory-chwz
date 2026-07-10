<script setup lang="ts">
import { Check, Copy, Download } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ICongregationDetailed } from '../types/congregation.types'
import { useCongregationExport } from '../composables/useCongregationExport'

const open = defineModel<boolean>('open', { required: true })

const { congregations } = defineProps<{ congregations: ICongregationDetailed[] }>()

const { t } = useI18n()
const { buildMarkdownContent, downloadMarkdown } = useCongregationExport()
const copied = ref(false)

const markdownContent = computed<string>(() => buildMarkdownContent(congregations))

async function handleCopy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(markdownContent.value)
    copied.value = true
    toast.success(t('common.copyToClipboard.success'))
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy markdown:', error)
    toast.error(t('congregations.export.copyError', 'Nie udało się skopiować do schowka'))
  }
}

function handleDownload(): void {
  downloadMarkdown(congregations)
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-3xl">
      <DialogHeader>
        <DialogTitle>
          {{ t('congregations.export.previewTitle', 'Podgląd eksportu Markdown') }}
        </DialogTitle>
        <DialogDescription>
          {{ t('congregations.export.previewDescription', 'Skopiuj treść lub pobierz plik .md') }}
        </DialogDescription>
      </DialogHeader>

      <pre class="max-h-[60vh] overflow-y-auto rounded-md border bg-muted p-4 font-mono text-sm whitespace-pre-wrap">{{ markdownContent }}</pre>

      <DialogFooter class="gap-2 sm:gap-0">
        <Button variant="outline" @click="handleCopy">
          <Check v-if="copied" class="size-4" />
          <Copy v-else class="size-4" />
          {{ copied ? t('common.copyToClipboard.copied') : t('common.copyToClipboard.copy') }}
        </Button>
        <Button @click="handleDownload">
          <Download class="size-4" />
          {{ t('congregations.export.download', 'Pobierz') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
