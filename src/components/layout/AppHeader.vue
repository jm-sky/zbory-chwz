<script setup lang="ts">
import { ContactIcon, MailIcon, SettingsIcon, ShieldCheckIcon, ShieldIcon, UserIcon, UsersIcon } from 'lucide-vue-next'
import { type Component, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import UserNav from '@/components/layout/UserNav.vue'
import LogoText from '@/components/ui/LogoText.vue'
import { AdminRoutePaths } from '@/modules/admin/routes'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRouteNames } from '@/modules/auth/config/routes'
import { DirectoryRoutePaths } from '@/modules/directory/routes'
import { GovernanceRoutePaths } from '@/modules/governance/routes'
import { GroupsRoutePaths } from '@/modules/groups/routes'
import { SettingsRoutePaths } from '@/modules/settings/routes'
import { useUser } from '@/modules/user/composables/useUser'
import { UserRoutePaths } from '@/modules/user/routes'
import { PublicRoutePaths } from '@/router/publicRoutes'
import DarkModeToggle from '@/shared/components/DarkModeToggle.vue'
import { usePermissions } from '@/shared/composables/usePermissions'
import LocaleToggle from '@/shared/i18n/components/LocaleToggle.vue'
import HoverLink from '../ui/hover-link/HoverLink.vue'

const { t } = useI18n()
const router = useRouter()
const { profile } = useUser()
const { canAccessAdminPanel, can } = usePermissions()
const { logout, user: authUser } = useAuth()

// Use auth user if backend is enabled, otherwise use profile from localStorage
const user = computed(() => authUser.value ?? profile.value)

interface Link {
  to: string
  label: string
  icon?: Component
  hidden?: boolean
}

const coreLinks = computed<Link[]>(() => [
  {
    to: UserRoutePaths.profile,
    label: t('user.profile.title', 'Profile'),
    icon: UserIcon,
  },
  {
    to: SettingsRoutePaths.settings,
    label: t('settings.page.title', 'Settings'),
    icon: SettingsIcon,
  },
  {
    to: GroupsRoutePaths.list,
    label: t('groups.list.title', 'Grupy ludzi'),
    icon: UsersIcon,
  },
  {
    to: DirectoryRoutePaths.export,
    label: t('directory.export.title', 'Eksport adresów e-mail'),
    icon: MailIcon,
  },
  {
    to: DirectoryRoutePaths.persons,
    label: t('directory.persons.title', 'Przeglądarka osób'),
    icon: ContactIcon,
  },
  {
    to: GovernanceRoutePaths.roles,
    label: t('governance.nav.roles', 'Zarządzanie rolami'),
    icon: ShieldCheckIcon,
    hidden: !can('services.manage'),
  },
  {
    to: AdminRoutePaths.dashboard,
    label: t('admin.dashboard.title', 'Admin Dashboard'),
    icon: ShieldIcon,
    hidden: !canAccessAdminPanel.value,
  }
])

const navLinks = computed<Link[]>(() => [
  // Navigation links can be added here as needed
])

const handleLogout = async () => {
  try {
    await logout()
    toast.success(t('auth.logout_success', 'Logged out successfully'))
    await router.push({ name: AuthRouteNames.login })
  } catch (error) {
    console.error('Logout error:', error)
    toast.error(t('auth.logout_error', 'Failed to logout'))
  }
}
</script>

<template>
  <header class="fixed left-0 top-0 z-50 w-full border-b bg-background/75 backdrop-blur-sm">
    <div class="mx-auto flex h-(--header-height) items-center px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-start gap-6">
        <RouterLink :to="PublicRoutePaths.landing" class="flex items-center gap-2 hover:brightness-80 hover:scale-103 transition-all ease-in-out duration-300">
          <LogoText />
        </RouterLink>
      </div>

      <nav v-if="navLinks.length > 0" class="hidden md:flex items-center gap-6 text-sm ml-6">
        <template v-for="link in navLinks" :key="link.to">
          <HoverLink :to="link.to">
            {{ link.label }}
          </HoverLink>
        </template>
      </nav>

      <div class="flex flex-1 items-center justify-end gap-x-2 mr-1 md:mr-6">
        <nav class="flex items-center gap-x-1">
          <LocaleToggle />
          <DarkModeToggle />
          <UserNav
            :core-links
            :user-name="user?.name ?? t('user.guest')"
            :user-email="user?.email"
            :user-avatar="user?.avatarUrl"
            @logout="handleLogout"
          >
            <template #menu-items>
              <!-- Add menu items here if needed -->
            </template>
          </UserNav>
        </nav>
      </div>
    </div>
  </header>
</template>
