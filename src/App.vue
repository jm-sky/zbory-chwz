<script setup lang="ts">
import PwaUpdatePrompt from '@/components/PwaUpdatePrompt.vue'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import 'vue-sonner/style.css'
import LoginModal from './shared/components/LoginModal.vue'
import { useAppInitialization } from './shared/composables/useAppInitialization'

const { isInitialized } = useAppInitialization()
</script>

<template>
  <TooltipProvider>
    <RouterView :is-initialized />
    <LoginModal />
    <PwaUpdatePrompt />
    <Toaster rich-colors />
  </TooltipProvider>
</template>

<style scoped></style>
