import type { RouteRecordRaw } from 'vue-router'

export const DirectoryRoutePaths = {
  export: '/people-directory',
} as const

export const DirectoryRouteNames = {
  export: 'people-directory-export',
} as const

export const directoryRoutes: RouteRecordRaw[] = [
  {
    path: DirectoryRoutePaths.export,
    name: DirectoryRouteNames.export,
    component: () => import('@/modules/directory/pages/DirectoryExportPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, title: 'directory.export.title' },
  },
]
