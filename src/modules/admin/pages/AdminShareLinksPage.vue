<script setup lang="ts">
import { Link2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import CommonPageHeader from '@/components/layout/CommonPageHeader.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import ShareLinksSection from '@/modules/congregations/components/ShareLinksSection.vue'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6 w-full max-w-full">
      <CommonPageHeader
        :icon="Link2"
        :label="t('admin.shareLinks.title', 'Linki udostępniania')"
        :description="t('admin.shareLinks.subtitle', 'Twórz linki dające dostęp do wszystkich opublikowanych zborów bez logowania')"
      />

      <ShareLinksSection />
    </div>
  </AuthenticatedLayout>
</template>
