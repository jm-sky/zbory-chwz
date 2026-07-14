<script setup lang="ts">
import { Clock, Mail, MapPin, Phone, User } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'
import { formatPhoneNumber } from '@/shared/utils/formatPhone'
import type { ICongregationDetail } from '../types/congregation.types'
import { formatAddress, formatServiceTimes } from '../utils/congregationDisplay'

const { congregation } = defineProps<{
  congregation: ICongregationDetail
}>()

const { t } = useI18n()
</script>

<template>
  <div class="space-y-6 pb-4 sm:pb-6">
    <!-- Address -->
    <div v-if="formatAddress(congregation)">
      <div class="flex items-center gap-3">
        <MapPin class="size-5 shrink-0 text-muted-foreground" />
        <h3 class="text-sm font-medium text-muted-foreground">
          {{ t('congregations.detail.address') }}
        </h3>
      </div>
      <p class="mt-1 pl-8 text-foreground">
        {{ formatAddress(congregation) }}
      </p>
    </div>

    <!-- Service Times -->
    <div v-if="congregation.service_times.length > 0">
      <div class="flex items-center gap-3">
        <Clock class="size-5 shrink-0 text-muted-foreground" />
        <h3 class="text-sm font-medium text-muted-foreground">
          {{ t('congregations.detail.serviceTimes') }}
        </h3>
      </div>
      <p class="mt-1 pl-8 text-foreground">
        {{ formatServiceTimes(congregation.service_times) }}
      </p>
    </div>

    <!-- Contacts -->
    <div v-if="congregation.card_contacts.length > 0">
      <div class="flex items-center gap-3">
        <User class="size-5 shrink-0 text-muted-foreground" />
        <h3 class="text-sm font-medium text-muted-foreground">
          {{ t('congregations.detail.contacts') }}
        </h3>
      </div>
      <div class="mt-2 space-y-4 pl-8">
        <div
          v-for="(contact, contactIndex) in congregation.card_contacts"
          :key="`contact-${contactIndex}`"
          class="space-y-1"
        >
          <div>
            <span class="font-medium text-foreground">{{ contact.name }}</span>
            <span v-if="contact.title" class="text-muted-foreground">
              {{ ` - ${contact.title}` }}
            </span>
          </div>
          <p v-if="contact.description" class="text-sm text-muted-foreground">
            {{ contact.description }}
          </p>
          <div v-if="contact.phone || contact.email" class="space-y-1">
            <a
              v-if="contact.phone"
              :href="`tel:${contact.phone}`"
              class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Phone class="size-3.5" />
              <span>{{ formatPhoneNumber(contact.phone) }}</span>
            </a>
            <a
              v-if="contact.email"
              :href="`mailto:${contact.email}`"
              class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Mail class="size-3.5" />
              <span class="break-all">{{ contact.email }}</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Hidden contacts (editors only) -->
    <div v-if="congregation.hidden_contacts?.length">
      <div class="flex items-center gap-3 opacity-60">
        <User class="size-5 shrink-0 text-muted-foreground" />
        <h3 class="text-sm font-medium text-muted-foreground">
          {{ t('congregations.detail.hiddenContacts') }}
        </h3>
      </div>
      <div class="mt-2 space-y-4 pl-8 opacity-60">
        <div
          v-for="(contact, contactIndex) in congregation.hidden_contacts"
          :key="`hidden-contact-${contactIndex}`"
          class="space-y-1"
        >
          <div>
            <span class="font-medium text-foreground">{{ contact.name }}</span>
            <span v-if="contact.title" class="text-muted-foreground">
              {{ ` - ${contact.title}` }}
            </span>
          </div>
          <p v-if="contact.description" class="text-sm text-muted-foreground">
            {{ contact.description }}
          </p>
          <div v-if="contact.phone || contact.email" class="space-y-1">
            <a
              v-if="contact.phone"
              :href="`tel:${contact.phone}`"
              class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Phone class="size-3.5" />
              <span>{{ formatPhoneNumber(contact.phone) }}</span>
            </a>
            <a
              v-if="contact.email"
              :href="`mailto:${contact.email}`"
              class="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <Mail class="size-3.5" />
              <span class="break-all">{{ contact.email }}</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Branches -->
    <div v-if="congregation.branches.length > 0">
      <h3 class="mb-2 text-sm font-medium text-muted-foreground">
        {{ t('congregations.detail.branches') }}
      </h3>
      <div class="flex flex-wrap gap-2">
        <Badge v-for="branch in congregation.branches" :key="branch.id" variant="secondary">
          {{ branch.name }}
        </Badge>
      </div>
    </div>
  </div>
</template>
