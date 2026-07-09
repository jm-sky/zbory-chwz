import type { RouteRecordRaw } from 'vue-router'

export const CongregationRoutePaths = {
  list: import.meta.env.VITE_CONGREGATIONS_LIST_PATH ?? '/congregations',
  edit: import.meta.env.VITE_CONGREGATIONS_EDIT_PATH ?? '/congregations/:id/edit',
  editById: (id: string) => `/congregations/${id}/edit`,
} as const

export const CongregationRouteNames = {
  list: 'congregations',
  edit: 'congregationEdit',
} as const

export const congregationRoutes: RouteRecordRaw[] = [
  {
    path: CongregationRoutePaths.list,
    name: CongregationRouteNames.list,
    component: () => import('@/pages/LandingPage.vue'),
    meta: { title: 'congregations.list.title' },
  },
  {
    path: CongregationRoutePaths.edit,
    name: CongregationRouteNames.edit,
    component: () => import('@/modules/congregations/pages/EditCongregationPage.vue'),
    meta: { layout: 'authenticated', title: 'congregations.edit.title' },
  },
]
