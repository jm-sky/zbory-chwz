<!--
  AI Chat Window Component
  Main chat interface for AI interactions
-->
<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { useAiChat } from '../composables/useAiChat'
import { useAiContext } from '../composables/useAiContext'
import { useAiHistory } from '../composables/useAiHistory'
import { useAiStore } from '../store/useAiStore'
import AiChatHistorySidebar from './AiChatHistorySidebar.vue'
import AiChatInputSection from './AiChatInputSection.vue'
import AiChatMessage from './AiChatMessage.vue'
import AiChatTemplateMsgButton from './AiChatTemplateMsgButton.vue'
import AiChatWindowHeader from './AiChatWindowHeader.vue'
import AiContextConfig from './AiContextConfig.vue'

const { t } = useI18n()

const props = defineProps<{
  containerIds?: string[]
  restoreHistoryId?: string | null
}>()

const aiStore = useAiStore()
const { messages, isLoading, lastPrompt, lastStructuredOutput, sendMessage, hasMessages, restoreFromHistory } = useAiChat()
const { buildContextData } = useAiContext()
const { getHistoryItemById } = useAiHistory()

// Action execution has been removed with gear module
const executeAction = (..._args: unknown[]) => {
  console.warn('AI actions are not available without gear module')
}

const userMessage = ref('')
const showContextConfig = ref(false)
const includeContainerData = ref(true)
const showHistorySidebar = ref(false)

const emit = defineEmits<{
  close: []
}>()

onMounted(async () => {
  // Load settings and models on mount
  if (!aiStore.settings) {
    await aiStore.loadSettings()
  }
  if (aiStore.availableModels.length === 0) {
    await aiStore.loadModels()
  }

  // Restore history if restoreHistoryId is provided
  if (props.restoreHistoryId) {
    try {
      let historyItem = getHistoryItemById(props.restoreHistoryId)
      if (!historyItem) {
        // If not in store, try to load history detail from API
        const { aiApiService } = await import('../services/aiApiService')
        const detail = await aiApiService.getHistoryDetail(props.restoreHistoryId)
        // Transform detail to IAiHistoryItem format
        historyItem = {
          id: detail.id,
          operationType: detail.operationType as import('../types/chat').AiOperationType,
          finalPrompt: detail.inputData?.message || '',
          contextData: detail.inputData?.context,
          responseData: detail.outputData || {},
          model: detail.model,
          provider: detail.metadata?.provider || '',
          tokens: {
            input: detail.promptTokens || 0,
            output: detail.completionTokens || 0,
            total: detail.totalTokens || 0,
          },
          cost: {
            input: 0,
            output: 0,
            total: detail.costUsd || 0,
          },
          durationMs: detail.metadata?.durationMs,
          usedOwnToken: detail.metadata?.usedOwnToken || false,
          containerIds: detail.containerIds,
          createdAt: detail.createdAt,
        }
      }
      if (historyItem) {
        await restoreFromHistory(historyItem)
      }
    } catch (error) {
      console.error('Failed to restore history:', error)
    }
  }
})

const handleSend = async (): Promise<void> => {
  if (!userMessage.value.trim() || isLoading.value) return

  // Build context with actual container data if enabled
  const context: Record<string, unknown> = includeContainerData.value && props.containerIds
    ? buildContextData(props.containerIds)
    : {}

  const response = await sendMessage(userMessage.value, context)
  userMessage.value = ''

  // Execute structured output action if present
  if (response?.structured_output) {
    const containerId = props.containerIds?.[0]
    await executeAction(response.structured_output, containerId)
  }
}

const onTemplatePrompt = (prompt: string) => {
  userMessage.value = prompt
}

const handleRestoreFromSidebar = async (item: import('../types/history').IAiHistoryItem): Promise<void> => {
  try {
    await restoreFromHistory(item)
    showHistorySidebar.value = false
  } catch (error) {
    console.error('Failed to restore history from sidebar:', error)
  }
}
</script>

<template>
  <div class="flex flex-col h-full relative">
    <!-- History Sidebar Sheet -->
    <Sheet v-model:open="showHistorySidebar">
      <SheetContent side="left" class="w-[400px] sm:w-[540px] p-0">
        <AiChatHistorySidebar
          :container-ids="props.containerIds"
          @restore="handleRestoreFromSidebar"
        />
      </SheetContent>
    </Sheet>

    <!-- Header with model selector -->
    <AiChatWindowHeader
      v-model:show-context-config="showContextConfig"
      v-model:show-history-sidebar="showHistorySidebar"
      @close="emit('close')"
    />

    <!-- Context config (collapsible) -->
    <Transition
      enter-from-class="opacity-0 -translate-y-2"
      enter-active-class="transition-all duration-300"
      enter-to-class="opacity-100 translate-y-0"
      leave-from-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-300"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <AiContextConfig
        v-if="showContextConfig"
        @close="showContextConfig = false"
      />
    </Transition>

    <!-- Messages -->
    <div class="relative flex-1 overflow-y-auto p-2 md:p-4 space-y-4">
      <div v-if="!hasMessages" class="absolute bottom-0 left-0 w-full text-xs z-10 flex flex-nowrap whitespace-nowrap gap-4 px-4 overflow-x-auto">
        <AiChatTemplateMsgButton variant="whatsUnnecessary" @prompt="onTemplatePrompt" />
        <AiChatTemplateMsgButton variant="whatsNeeded" @prompt="onTemplatePrompt" />
        <AiChatTemplateMsgButton variant="addRandomItem" @prompt="onTemplatePrompt" />
      </div>

      <div v-if="!hasMessages" class="flex items-center justify-center h-full text-muted-foreground">
        <p class="text-sm">
          {{ t('ai.chat.startConversation') }}
        </p>
      </div>

      <AiChatMessage
        v-for="(message, index) in messages"
        :key="message.id"
        :message
        :debug-prompt="message.role === 'assistant' && index === messages.length - 1 ? lastPrompt : null"
        :debug-structured-output="message.role === 'assistant' && index === messages.length - 1 ? lastStructuredOutput : null"
      />

      <div v-if="isLoading" class="flex items-center gap-2">
        <Loader2 class="size-4 animate-spin" />
        <span class="text-sm text-muted-foreground">{{ t('ai.chat.thinking') }}</span>
      </div>
    </div>

    <!-- Input -->
    <AiChatInputSection
      v-model:user-message="userMessage"
      :container-ids="props.containerIds"
      :is-loading="isLoading"
      :include-container-data="includeContainerData"
      @send="handleSend"
      @toggle-context-config="showContextConfig = !showContextConfig"
    />
  </div>
</template>

