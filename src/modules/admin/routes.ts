import type { RouteRecordRaw } from 'vue-router'

export const AdminRoutePaths = {
  dashboard: '/admin',
  users: '/admin/users',
  limits: '/admin/limits',
  subscriptions: '/admin/subscriptions',
}

export const AdminRouteNames = {
  dashboard: 'admin-dashboard',
  users: 'admin-users',
  limits: 'admin-limits',
  subscriptions: 'admin-subscriptions',
}

export const adminRoutes: RouteRecordRaw[] = [
  {
    path: AdminRoutePaths.dashboard,
    name: AdminRouteNames.dashboard,
    component: () => import('@/modules/admin/pages/AdminDashboardPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.dashboard.title' },
  },
  {
    path: AdminRoutePaths.users,
    name: AdminRouteNames.users,
    component: () => import('@/modules/admin/pages/AdminUsersPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.users.title' },
  },
  {
    path: AdminRoutePaths.limits,
    name: AdminRouteNames.limits,
    component: () => import('@/modules/admin/pages/AdminLimitsPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.limits.title' },
  },
  {
    path: AdminRoutePaths.subscriptions,
    name: AdminRouteNames.subscriptions,
    component: () => import('@/modules/admin/pages/AdminSubscriptionsPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.subscriptions.title' },
  },
]
