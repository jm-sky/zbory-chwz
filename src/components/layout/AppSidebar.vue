<script setup lang="ts">
import { Info } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { PublicRoutePaths } from '@/router/publicRoutes'

const { t } = useI18n()
</script>

<template>
  <Sidebar collapsible="icon">
    <SidebarContent class="overflow-x-hidden max-h-[90vh] overflow-y-auto">
      <!-- Main navigation section -->
      <SidebarGroup>
        <SidebarGroupLabel>{{ t('navigation.main', 'Main') }}</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <!-- Navigation items can be added here -->
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <RouterLink v-slot="{ href, navigate, isActive }" :to="PublicRoutePaths.about" custom>
            <SidebarMenuButton
              :is-active="isActive"
              as="a"
              :href="href"
              @click="navigate"
            >
              <Info class="size-4" />
              <span>{{ t('common.pages.about', 'About') }}</span>
            </SidebarMenuButton>
          </RouterLink>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>

    <SidebarRail />
  </Sidebar>
</template>

