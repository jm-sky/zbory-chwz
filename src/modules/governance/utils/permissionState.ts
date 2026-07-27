import type { IGrantableRole } from '@/modules/congregations/types/church.types'

/**
 * A "deny" exception is global in the chain (architecture §2) — a deny set on a scope wider
 * than a single church silently blocks every church beneath it. The panel (G10) must warn
 * about this whenever the scope is community or region.
 */
export function isWideScope(scopeType: string): boolean {
  return scopeType === 'community' || scopeType === 'region'
}

/** Union of every permission that appears on any role — the exception catalog (G4/G10). */
export function permissionCatalog(roles: IGrantableRole[]): string[] {
  const all = new Set<string>()
  for (const role of roles) {
    for (const permission of role.permissions) all.add(permission)
  }
  return [...all].sort()
}

/** Permissions granted by whichever of `heldRoleNames` appear in `roles`. */
export function inheritedPermissions(roles: IGrantableRole[], heldRoleNames: string[]): Set<string> {
  const held = new Set(heldRoleNames)
  const granted = new Set<string>()
  for (const role of roles) {
    if (held.has(role.name)) {
      for (const permission of role.permissions) granted.add(permission)
    }
  }
  return granted
}
