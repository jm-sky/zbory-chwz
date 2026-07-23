import type { RouteRecordRaw } from 'vue-router'

export const GroupsRoutePaths = {
  list: '/groups',
  detail: '/groups/:id',
  detailById: (id: string) => `/groups/${id}`,
} as const

export const GroupsRouteNames = {
  list: 'groups-list',
  detail: 'groups-detail',
} as const

export const groupRoutes: RouteRecordRaw[] = [
  {
    path: GroupsRoutePaths.list,
    name: GroupsRouteNames.list,
    component: () => import('@/modules/groups/pages/GroupsListPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, title: 'groups.list.title' },
  },
  {
    path: GroupsRoutePaths.detail,
    name: GroupsRouteNames.detail,
    component: () => import('@/modules/groups/pages/GroupDetailPage.vue'),
    meta: { layout: 'authenticated', requiresAuth: true, title: 'groups.detail.title' },
    props: true,
  },
]
