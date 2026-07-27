import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

let isAuthenticatedValue = true
const mockGet = vi.fn()

vi.mock('@/modules/auth/store/useAuthStore', () => ({
  useAuthStore: () => ({
    get isAuthenticated() {
      return isAuthenticatedValue
    },
  }),
}))

vi.mock('@/shared/services/apiClient', () => ({
  apiClient: { get: mockGet },
}))

vi.mock('@/shared/config/config', () => ({
  config: { backend: { enabled: true } },
}))

const { permissionGuard } = await import('./permissionGuard')
const { AuthRouteNames } = await import('@/modules/auth/config/routes')
const { PublicRouteNames } = await import('@/router/publicRoutes')

function route(meta: Record<string, unknown> = {}): RouteLocationNormalized {
  return { meta, fullPath: '/governance/roles' } as unknown as RouteLocationNormalized
}

describe('permissionGuard', () => {
  beforeEach(() => {
    mockGet.mockReset()
    isAuthenticatedValue = true
  })

  it('allows navigation when the route has no requiresPermission meta', async () => {
    const next = vi.fn()
    await permissionGuard(route(), route(), next)
    expect(next).toHaveBeenCalledWith()
    expect(mockGet).not.toHaveBeenCalled()
  })

  it('redirects unauthenticated visitors to login with redirectTo', async () => {
    isAuthenticatedValue = false
    const next = vi.fn()
    await permissionGuard(route({ requiresPermission: 'services.manage' }), route(), next)
    expect(next).toHaveBeenCalledWith({ name: AuthRouteNames.login, query: { redirectTo: '/governance/roles' } })
  })

  it('redirects to home when the user lacks the permission (pastor)', async () => {
    mockGet.mockResolvedValue({ data: { isAdmin: false, isOwner: false, scopes: [] } })
    const next = vi.fn()
    await permissionGuard(route({ requiresPermission: 'services.manage' }), route(), next)
    expect(next).toHaveBeenCalledWith({ name: PublicRouteNames.landing })
  })

  it('allows navigation when the user has the permission (bishop)', async () => {
    mockGet.mockResolvedValue({
      data: { isAdmin: false, isOwner: false, scopes: [{ scopeType: 'community', scopeId: 'c1', permissions: ['services.manage'] }] },
    })
    const next = vi.fn()
    await permissionGuard(route({ requiresPermission: 'services.manage' }), route(), next)
    expect(next).toHaveBeenCalledWith()
  })

  it('allows navigation for admins even with no explicit scopes', async () => {
    mockGet.mockResolvedValue({ data: { isAdmin: true, isOwner: false, scopes: [] } })
    const next = vi.fn()
    await permissionGuard(route({ requiresPermission: 'services.manage' }), route(), next)
    expect(next).toHaveBeenCalledWith()
  })

  it('redirects to home if the permissions request fails', async () => {
    mockGet.mockRejectedValue(new Error('network error'))
    const next = vi.fn()
    await permissionGuard(route({ requiresPermission: 'services.manage' }), route(), next)
    expect(next).toHaveBeenCalledWith({ name: PublicRouteNames.landing })
  })
})
