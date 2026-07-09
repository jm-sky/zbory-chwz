<script setup lang="ts">
import { Check, Copy } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'

const { t } = useI18n()
const copied = ref(false)

const aiContextMarkdown = computed(() => {
  return `# Zbory CHWZ - AI Context

## Overview
Zbory CHWZ is a full-stack web application for managing and publicly presenting congregation data for the Christian Community of Free Pentecostals (CHWZ). It is designed for congregation administrators, church leadership, and the public seeking congregation information.

## Key Capabilities
- **Multi-User Platform** - Secure user accounts with authentication and authorization
- **Hybrid Architecture** - Local browser settings, congregation data synced in the cloud
- **Congregation Management** - Profiles, addresses, service times, and contact persons
- **Publication Workflow** - Draft, published, and verification statuses
- **AI Context** - Markdown description for AI assistants

## Core Features

### Congregation Profiles
- Manage congregation name, description, and publication status
- Status indicators for draft, published, and unverified congregations
- Governance workflow for publishing and verifying congregation data

### Addresses & Service Times
- Address data: street, city, postal code, province, country
- Service times — day and time of worship services
- Contact persons — name, role, email, phone for congregation leaders
- Multiple service times and contact persons per congregation

### Public Views
- Public congregation directory with basic information
- Congregation detail pages with address, service times, and contacts
- Admin dashboard for managing users and congregations

### Search & Filtering
- Search congregations by name, city, or address
- Filter by publication status and location
- Sort by name or city

## Business Features

### User Management & Security
- Email/password authentication with secure password hashing
- OAuth social login (Google, Facebook, GitHub)
- Email verification
- Two-factor authentication (2FA) - TOTP and WebAuthn (passkeys)
- Password management - reset and change
- reCAPTCHA v3 protection
- JWT tokens with automatic refresh
- GDPR-compliant account deletion

### User Profile
- Profile management - name, email, preferences
- Avatar support from OAuth providers
- Preferred settings - language, theme
- Security settings - manage 2FA methods

### Multi-Language Support
- English, Polish, and Russian fully supported
- Automatic locale detection
- Manual language switching
- All UI text, validation messages, and emails localized

### Theming
- Dark mode with system preference detection
- Theme persistence per user account

## Technical Stack

### Frontend
- Vue 3.5+ with TypeScript & Composition API
- Pinia for state management
- Vue Router for navigation
- TailwindCSS v4 + shadcn-vue components
- VeeValidate + Zod for form validation
- TanStack Query for server state management
- vue-i18n for internationalization

### Backend
- FastAPI (Python) with async/await
- PostgreSQL database
- SQLAlchemy ORM with async support
- JWT authentication with refresh tokens
- Rate limiting and reCAPTCHA protection
- Modular architecture (auth, congregations, admin, two-factor, email)

## Architecture
- **Server-Side Data**: Congregation data stored in PostgreSQL via API
- **Client-Side Settings**: User preferences persisted in localStorage
- **Module-Based Frontend** - Each feature is self-contained in modules
- **Backend Modules** - FastAPI modular pattern with routers, services, repositories`
})

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(aiContextMarkdown.value)
    copied.value = true
    toast.success(t('aiContext.copied', 'Context copied to clipboard'))
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    toast.error(t('common.error'))
    console.error('Error copying to clipboard:', error)
  }
}
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-8">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('about.title', 'About Zbory CHWZ') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('about.subtitle', 'Application for managing and publicly presenting congregations of the Christian Community of Free Pentecostals') }}
        </p>
      </div>

      <!-- Table of Contents -->
      <nav class="flex flex-row flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <a href="#overview" class="text-primary hover:underline">
          {{ t('about.overview.title', 'Overview') }}
        </a>
        <span>|</span>
        <a href="#capabilities" class="text-primary hover:underline">
          {{ t('about.capabilities.title', 'Key Capabilities') }}
        </a>
        <span>|</span>
        <a href="#core-features" class="text-primary hover:underline">
          {{ t('about.coreFeatures.title', 'Core Features') }}
        </a>
        <span>|</span>
        <a href="#business-features" class="text-primary hover:underline">
          {{ t('about.businessFeatures.title', 'Business Features') }}
        </a>
        <span>|</span>
        <a href="#technical-stack" class="text-primary hover:underline">
          {{ t('about.technical.title', 'Technical Stack') }}
        </a>
        <span>|</span>
        <a href="#ai-context" class="text-primary hover:underline">
          {{ t('aiContext.title', 'AI Context') }}
        </a>
      </nav>

      <!-- Overview -->
      <section id="overview" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.overview.title', 'Overview') }}
        </h2>
        <p class="text-muted-foreground">
          {{ t('about.overview.description', 'Zbory CHWZ is a full-stack application for managing and publicly presenting CHWZ congregation data. It combines an intuitive interface with a robust backend to provide secure multi-user data management with cloud synchronization across devices.') }}
        </p>
      </section>

      <!-- Key Capabilities -->
      <section id="capabilities" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.capabilities.title', 'Key Capabilities') }}
        </h2>
        <ul class="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{{ t('about.capabilities.multiUser', 'Multi-User Platform - Secure user accounts with authentication and authorization') }}</li>
          <li>{{ t('about.capabilities.hybrid', 'Hybrid Architecture - Works offline with localStorage, syncs with cloud when online') }}</li>
          <li>{{ t('about.capabilities.organization', 'Congregation Management — profiles, addresses, service times, and contact persons') }}</li>
          <li>{{ t('about.capabilities.metadata', 'Publication Status — draft, published, needs verification') }}</li>
          <li>{{ t('about.capabilities.portability', 'AI Context — application description in Markdown format for AI assistants') }}</li>
        </ul>
      </section>

      <!-- Core Features -->
      <section id="core-features" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.coreFeatures.title', 'Core Features') }}
        </h2>
        <div class="space-y-6">
          <div id="container-system" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.coreFeatures.containers.title', 'Congregation Profiles') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.coreFeatures.containers.multiple', 'Manage congregation name, description, and publication status (draft, published, unverified)') }}</li>
              <li>{{ t('about.coreFeatures.containers.hierarchical', 'Organizational hierarchy — branches and regions (planned)') }}</li>
              <li>{{ t('about.coreFeatures.containers.colors', 'Status indicators — quick identification of publication and verification state') }}</li>
              <li>{{ t('about.coreFeatures.containers.metadata', 'Congregation metadata — description, status, visibility settings') }}</li>
              <li>{{ t('about.coreFeatures.containers.cycle', 'Publishing and verification workflow for congregation data') }}</li>
            </ul>
          </div>

          <div id="item-management" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.coreFeatures.items.title', 'Addresses & Service Times') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.coreFeatures.items.rich', 'Address data: street, city, postal code, province, country, publication status') }}</li>
              <li>{{ t('about.coreFeatures.items.categorization', 'Service times — day and time of worship services') }}</li>
              <li>{{ t('about.coreFeatures.items.status', 'Contact persons — name, role, email, and phone for congregation leaders') }}</li>
              <li>{{ t('about.coreFeatures.items.priority', 'Multiple service times and contact persons per congregation') }}</li>
              <li>{{ t('about.coreFeatures.items.expiration', 'Data validation and required fields for published profiles') }}</li>
            </ul>
          </div>

          <div id="analytics-insights" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.coreFeatures.analytics.title', 'Public Views') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.coreFeatures.analytics.weight', 'Congregation list — public directory with basic information') }}</li>
              <li>{{ t('about.coreFeatures.analytics.readiness', 'Congregation details — address, service times, and contact info') }}</li>
              <li>{{ t('about.coreFeatures.analytics.charts', 'Admin dashboard — manage users and congregations') }}</li>
              <li>{{ t('about.coreFeatures.analytics.statistics', 'Statistics — number of users and published congregations') }}</li>
            </ul>
          </div>

          <div id="search-filtering" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.coreFeatures.search.title', 'Search & Filtering') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.coreFeatures.search.smart', 'Search congregations by name, city, or address') }}</li>
              <li>{{ t('about.coreFeatures.search.filtering', 'Filter by publication status and location') }}</li>
              <li>{{ t('about.coreFeatures.search.sorting', 'Sort by name or city') }}</li>
              <li>{{ t('about.coreFeatures.search.expired', 'Highlight congregations requiring verification') }}</li>
            </ul>
          </div>

          <div id="import-export" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.coreFeatures.importExport.title', 'Administration') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.coreFeatures.importExport.json', 'User management — roles, email verification, 2FA') }}</li>
              <li>{{ t('about.coreFeatures.importExport.markdown', 'Congregation management — edit, publish, and unpublish') }}</li>
              <li>{{ t('about.coreFeatures.importExport.csv', 'Admin panel — overview of all congregations and users') }}</li>
              <li>{{ t('about.coreFeatures.importExport.crossDevice', 'Multi-device access — cloud data synchronization') }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Business Features -->
      <section id="business-features" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.businessFeatures.title', 'Business Features') }}
        </h2>
        <div class="space-y-6">
          <div id="user-management-security" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.businessFeatures.security.title', 'User Management & Security') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.businessFeatures.security.auth', 'User registration & login - email/password authentication with secure password hashing') }}</li>
              <li>{{ t('about.businessFeatures.security.oauth', 'OAuth social login - sign in with Google (GitHub support planned)') }}</li>
              <li>{{ t('about.businessFeatures.security.email', 'Email verification - confirm email addresses for account security') }}</li>
              <li>{{ t('about.businessFeatures.security.2fa', 'Two-factor authentication (2FA) - TOTP (authenticator apps) and WebAuthn (passkeys/security keys)') }}</li>
              <li>{{ t('about.businessFeatures.security.password', 'Password management - reset forgotten passwords, change password for authenticated users') }}</li>
              <li>{{ t('about.businessFeatures.security.recaptcha', 'reCAPTCHA v3 protection - invisible bot protection on login, registration, and password reset') }}</li>
              <li>{{ t('about.businessFeatures.security.session', 'Session management - JWT tokens with automatic refresh, secure logout') }}</li>
              <li>{{ t('about.businessFeatures.security.deletion', 'Account deletion - GDPR-compliant soft delete with confirmation') }}</li>
            </ul>
          </div>

          <div id="user-profile" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.businessFeatures.profile.title', 'User Profile') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.businessFeatures.profile.management', 'Profile management - update name, email, and preferences') }}</li>
              <li>{{ t('about.businessFeatures.profile.avatar', 'Avatar support - OAuth providers automatically provide profile pictures') }}</li>
              <li>{{ t('about.businessFeatures.profile.settings', 'Preferred settings — language, theme preferences') }}</li>
              <li>{{ t('about.businessFeatures.profile.security', 'Security settings - manage 2FA methods, view security status') }}</li>
            </ul>
          </div>

          <div id="multi-language-support" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.businessFeatures.i18n.title', 'Multi-Language Support') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.businessFeatures.i18n.languages', 'English, Polish, and Russian fully supported') }}</li>
              <li>{{ t('about.businessFeatures.i18n.detection', 'Automatic locale detection from browser') }}</li>
              <li>{{ t('about.businessFeatures.i18n.switching', 'Manual language switching in settings') }}</li>
              <li>{{ t('about.businessFeatures.i18n.localized', 'All UI text, validation messages, and emails localized') }}</li>
            </ul>
          </div>

          <div id="theming" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.businessFeatures.theming.title', 'Theming') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>{{ t('about.businessFeatures.theming.dark', 'Dark mode - full dark theme support with system preference detection') }}</li>
              <li>{{ t('about.businessFeatures.theming.persistence', 'Theme persistence - settings saved per user account') }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Technical Stack -->
      <section id="technical-stack" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('about.technical.title', 'Technical Stack') }}
        </h2>
        <div class="space-y-4">
          <div id="frontend" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.technical.frontend.title', 'Frontend') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>Vue 3.5+ with TypeScript & Composition API</li>
              <li>Pinia for state management</li>
              <li>Vue Router for navigation</li>
              <li>TailwindCSS v4 + shadcn-vue components</li>
              <li>VeeValidate + Zod for form validation</li>
              <li>TanStack Query for server state management</li>
              <li>vue-i18n for internationalization</li>
            </ul>
          </div>

          <div id="backend" class="space-y-2 scroll-mt-18">
            <h3 class="text-xl font-semibold">
              {{ t('about.technical.backend.title', 'Backend') }}
            </h3>
            <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>FastAPI (Python) with async/await</li>
              <li>PostgreSQL database</li>
              <li>SQLAlchemy ORM with async support</li>
              <li>JWT authentication with refresh tokens</li>
              <li>Rate limiting and reCAPTCHA protection</li>
              <li>Modular architecture (auth, two-factor, email)</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- AI Context -->
      <section id="ai-context" class="space-y-4 scroll-mt-18">
        <h2 class="text-2xl font-semibold">
          {{ t('aiContext.title', 'AI Context') }}
        </h2>
        <p class="text-muted-foreground">
          {{ t('aiContext.subtitle', 'Short description of Zbory CHWZ in Markdown format for AI assistants like ChatGPT') }}
        </p>

        <Card>
          <CardHeader>
            <div class="flex items-center justify-between">
              <div>
                <CardTitle>
                  {{ t('aiContext.card.title', 'Copy Context to Clipboard') }}
                </CardTitle>
                <CardDescription>
                  {{ t('aiContext.card.description', 'Click the button below to copy the context description. You can then paste it into ChatGPT or other AI assistants to provide context about Zbory CHWZ.') }}
                </CardDescription>
              </div>
              <Button @click="handleCopy">
                <Copy v-if="!copied" class="size-4" />
                <Check v-else class="size-4" />
                {{ copied ? t('common.copyToClipboard.copied') : t('common.copyToClipboard.copy') }}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre class="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded-md border overflow-x-auto max-h-[600px] overflow-y-auto">{{ aiContextMarkdown }}</pre>
          </CardContent>
        </Card>
      </section>
    </div>
  </AuthenticatedLayout>
</template>

