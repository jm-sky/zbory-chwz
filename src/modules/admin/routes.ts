import type { RouteRecordRaw } from 'vue-router'

export const AdminRoutePaths = {
  dashboard: '/admin',
  users: '/admin/users',
  congregations: '/admin/congregations',
  congregationImport: '/admin/congregations/import',
}

export const AdminRouteNames = {
  dashboard: 'admin-dashboard',
  users: 'admin-users',
  congregations: 'admin-congregations',
  congregationImport: 'admin-congregation-import',
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
    path: AdminRoutePaths.congregations,
    name: AdminRouteNames.congregations,
    component: () => import('@/modules/admin/pages/AdminCongregationsPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.congregations.title' },
  },
  {
    path: AdminRoutePaths.congregationImport,
    name: AdminRouteNames.congregationImport,
    component: () => import('@/modules/admin/pages/AdminCongregationImportPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, requiresAdmin: true, title: 'admin.congregationImport.title' },
  },
]
