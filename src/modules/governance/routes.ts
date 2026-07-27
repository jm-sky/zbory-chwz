import type { RouteRecordRaw } from 'vue-router'

export const GovernanceRoutePaths = {
  roles: '/governance/roles',
} as const

export const GovernanceRouteNames = {
  roles: 'governance-roles',
} as const

export const governanceRoutes: RouteRecordRaw[] = [
  {
    path: GovernanceRoutePaths.roles,
    name: GovernanceRouteNames.roles,
    component: () => import('@/modules/governance/pages/GovernanceRolesPage.vue'),
    meta: {
      layout: 'authenticated',
      requiresAuth: true,
      requiresPermission: 'services.manage',
      title: 'governance.roles.title',
    },
  },
]
