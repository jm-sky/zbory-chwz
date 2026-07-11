import type { RouteRecordRaw } from 'vue-router'

export const DirectoryRoutePaths = {
  export: '/people-directory',
  persons: '/people-directory/persons',
} as const

export const DirectoryRouteNames = {
  export: 'people-directory-export',
  persons: 'people-directory-persons',
} as const

export const directoryRoutes: RouteRecordRaw[] = [
  {
    path: DirectoryRoutePaths.export,
    name: DirectoryRouteNames.export,
    component: () => import('@/modules/directory/pages/DirectoryExportPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, title: 'directory.export.title' },
  },
  {
    path: DirectoryRoutePaths.persons,
    name: DirectoryRouteNames.persons,
    component: () => import('@/modules/directory/pages/PersonBrowserPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, title: 'directory.persons.title' },
  },
]
