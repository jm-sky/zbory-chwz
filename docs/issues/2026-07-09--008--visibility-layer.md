# Unified visibility layer

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 3)  
**Depends on:** [#007](./2026-07-09--007--acl-roles-permissions.md)

## Problem

Visibility is inconsistent: `tenant.status`, address `status`, and a planned `is_public` flag on contact persons. Need one mechanism for read access separate from edit permissions.

## Scope

- [ ] Enum: `hidden | public | authenticated | pastors`
- [ ] Add `visibility` to `churches`, `congregation_contact_persons`, `congregation_service_times`
- [ ] Migration: map existing published/draft states to visibility levels
- [ ] `VisibilityService.filter(query, user, scope)` for API responses
- [ ] Public endpoints return only `public` content for guests
- [ ] Authenticated users see `public` + `authenticated`
- [ ] Pastor-scoped users see `pastors` content in their scope
- [ ] Editor UI: visibility selector on congregation edit forms
- [ ] Communities default to `hidden`

## Acceptance criteria

- Guest on public church page sees only `public` contact persons and service times
- Logged-in member sees `authenticated` content
- Pastor sees `pastors`-level fields for own church
- Changing visibility does not grant edit rights

## Notes

- Supersedes ROADMAP `is_public` contact flag — use `visibility` instead
