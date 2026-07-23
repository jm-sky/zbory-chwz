# Unified visibility layer

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 3)  
**Depends on:** [#007](./2026-07-09--007--acl-roles-permissions.md)

## Problem

Visibility is inconsistent: `tenant.status`, address `status` (`draft`, `published`, `published_unverified`, `need_verification`), and a planned `is_public` flag on contact persons. Need one mechanism for **read access** separate from edit permissions and separate from **editorial workflow status**.

Current public list (`GET /congregations/detailed`) filters by `address.status in (published, published_unverified)` — must migrate to `churches.visibility`.

## Scope

- [ ] PostgreSQL enum or check constraint: `hidden | public | authenticated | pastors`
- [ ] Add `visibility` to `churches`, `service_assignments` (show on card), `persons` or assignment (phone/email), `congregation_service_times`
- [ ] Deprecate `congregation_contact_persons` — see [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)
- [ ] Migration script — map existing states:

  | Source | Target |
  |--------|--------|
  | `address.status` = `draft` / `need_verification` | church `visibility` = `hidden` |
  | `address.status` = `published` / `published_unverified` | church `visibility` = `public` |
  | service assignments (ex contact persons) | default `public` on card; phone/email per [#012](./2026-07-09--012--unify-services-remove-contact-persons.md) |
  | service times | default `public` |

- [ ] Keep `address.status` for workflow (verification queue) — **do not** remove
- [ ] `VisibilityService.can_view(level, user, church_scope)` 
- [ ] `VisibilityService.filter_fields(serializer, user)` for API responses
- [ ] Public endpoints: only `public` content for guests
- [ ] Authenticated: `public` + `authenticated`
- [ ] `pastors` visibility: users with bishop/pastor/diacon service (via ACL), in scope
- [ ] Editor UI: visibility selector per entity on congregation edit forms
- [ ] Communities default to `hidden`

## Acceptance criteria

- Guest on public church page sees only `public` contact persons and service times
- Logged-in member without role sees `authenticated` content, not `pastors`
- Pastor sees `pastors`-level fields for own church only (not other churches)
- `churches.visibility != public` → public URL returns 404
- Changing visibility does not grant edit rights

## Suggestions

- Church page publish toggle sets `churches.visibility`, not `tenant.status`.
- Add `visibility` column with default `hidden` for new churches — explicit publish required.
- Unit-test `VisibilityService` independently of HTTP layer.
- Document matrix in API OpenAPI descriptions for public vs authenticated routes.

## Notes

- Supersedes ROADMAP `is_public` contact flag — use `visibility` instead
- `published_unverified` workflow becomes: `visibility = public` + `address.status = published_unverified` (shows badge in admin, still public)

## Decisions (2026-07-09)

- `pastors` visibility = users with ACL from bishop/pastor/diacon service types (not plain authenticated)
- `published_unverified` stays as workflow badge alongside `visibility = public`
