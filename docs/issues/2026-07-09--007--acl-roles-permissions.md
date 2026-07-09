# ACL — roles and permission resolution

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 2)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md)

## Problem

Access is controlled by a single `tenant_memberships.role` string. Real church organization needs separated roles (Pastor, Bishop, …) and granular permissions with per-user exceptions.

## Scope

- [ ] Tables: `roles`, `role_permissions`, `user_role_assignments`, `user_permissions`
- [ ] `PermissionService` with resolution order: role defaults → user exceptions (deny wins) → admin override
- [ ] Scope inheritance: branch → church → region → community
- [ ] FastAPI dependency `RequirePermission(permission, scope)`
- [ ] Seed MVP roles: Admin, Bishop, Regional Bishop, Pastor, Diacon, Branch responsible
- [ ] Seed MVP permissions (see implementation plan table)
- [ ] Replace tenant membership checks on congregation write endpoints
- [ ] Unit tests for resolution edge cases

## Acceptance criteria

- Pastor can edit own church, not a sibling church in same city
- Bishop can edit all churches in community
- `deny` user exception blocks a role-granted permission
- Global admin bypasses scope checks

## Open questions (review before coding)

- Exact permission list for Diacon role
- Whether Regional Bishop is a separate role or scoped Bishop assignment
