import { adminRoutes } from '@/modules/admin/routes'
import { AuthRouteNames, AuthRoutePaths, authRoutes } from '@/modules/auth/config/routes'
import { congregationRoutes } from '@/modules/congregations/routes'
import { directoryRoutes } from '@/modules/directory/routes'
import { governanceRoutes } from '@/modules/governance/routes'
import { groupRoutes } from '@/modules/groups/routes'
import { settingsRoutes } from '@/modules/settings/routes'
import { userRoutes } from '@/modules/user/routes'
import { publicRoutes } from '@/router/publicRoutes'
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  // Landing page (public)
  ...publicRoutes.filter(route => route.name === 'landing'),
  // Dashboard
  {
    path: AuthRoutePaths.dashboard,
    name: AuthRouteNames.dashboard,
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { layout: 'authenticated', title: 'navigation.dashboard' },
  },
  // Other public pages (about, cookies, privacy, terms, contact)
  ...publicRoutes.filter(route => route.name !== 'landing' && route.name !== 'not-found'),
  // Module routes
  ...authRoutes,
  ...adminRoutes,
  ...congregationRoutes,
  ...directoryRoutes,
  ...governanceRoutes,
  ...groupRoutes,
  ...settingsRoutes,
  ...userRoutes,
  // 404 catch-all route - must be last
  ...publicRoutes.filter(route => route.name === 'not-found'),
]
