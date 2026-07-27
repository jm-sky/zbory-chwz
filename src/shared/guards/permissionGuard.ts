import { AuthRouteNames } from '@/modules/auth/config/routes'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { PublicRouteNames } from '@/router/publicRoutes'
import { config } from '@/shared/config/config'
import { apiClient } from '@/shared/services/apiClient'
import type { NavigationGuardNext, RouteLocationNormalized, Router } from 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** ACL permission (e.g. 'services.manage') required to view this route. UX-only —
     * the API is the real authority (§10); a typo here just hides a menu item/page,
     * it never grants access the backend wouldn't otherwise allow. */
    requiresPermission?: string
  }
}

interface MePermissionsResponse {
  isAdmin: boolean
  isOwner: boolean
  scopes: { scopeType: string, scopeId: string, permissions: string[] }[]
}

/**
 * Fetches the permission check directly rather than going through the reactive
 * `usePermissions()` / TanStack Query cache: a navigation guard runs outside any
 * component's setup scope, so there's no guarantee the query has resolved by the time
 * the guard needs an answer (the composable is fine for reactive UI bindings — nav items,
 * page content — where a render a tick later is invisible; a guard needs a definite
 * answer before it decides whether to redirect).
 */
async function hasPermission(permission: string): Promise<boolean> {
  try {
    const { data } = await apiClient.get<MePermissionsResponse>('/churches/me/permissions')
    if (data.isAdmin || data.isOwner) return true
    return data.scopes.some(scope => scope.permissions.includes(permission))
  } catch {
    return false
  }
}

/**
 * Permission guard that checks `meta.requiresPermission` against /churches/me/permissions.
 * Should be called after authGuard (and after adminGuard, since admin/owner already
 * bypass every permission check).
 */
export async function permissionGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
): Promise<void> {
  // Skip permission checks if backend is disabled
  if (!config.backend.enabled) {
    next()
    return
  }

  const requiredPermission = to.meta.requiresPermission
  if (!requiredPermission) {
    next()
    return
  }

  const authStore = useAuthStore()

  if (!authStore.isAuthenticated) {
    next({ name: AuthRouteNames.login, query: { redirectTo: to.fullPath } })
    return
  }

  if (!(await hasPermission(requiredPermission))) {
    next({ name: PublicRouteNames.landing })
    return
  }

  next()
}

/**
 * Helper to install the permission guard on router.
 * Usage: protectPermissionRoutes(router)
 * Should be called after protectAdminRoutes.
 */
export function protectPermissionRoutes(router: Router): void {
  router.beforeEach(permissionGuard)
}
