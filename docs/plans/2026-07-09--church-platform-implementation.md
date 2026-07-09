# Church platform — implementation plan

**Status:** `planned`  
**Created:** 2026-07-09  
**Sources:**
- [2026-07-09--church-platform.md](./2026-07-09--church-platform.md) — model zborów, widoczność, URL
- [2026-07-09--organization-and-acl.md](./2026-07-09--organization-and-acl.md) — hierarchia organizacyjna i ACL

> **Note:** This is a first-pass implementation plan. Expect review and optimization before development starts.

## Goal

Build a multi-community church platform where:

- Organizational units form a hierarchy: **Community → Region → Church → Branch**
- **Roles/functions** (Pastor, Diacon, Bishop, …) are separate from **permissions**
- **Visibility** (who can see data) is separate from **edit permissions** (who can change data)
- Public congregation pages use stable, hierarchical URLs: `/kraj/miasto/slug-zboru`

## Current state (baseline)

| Area | Today | Gap |
|------|-------|-----|
| Congregation entity | `tenants` table + `tenant_memberships.role` | No community/region/branch hierarchy |
| Congregation data | `congregation_addresses`, `congregation_service_times`, `congregation_contact_persons` keyed by `tenant_id` | No slug, no country/city routing |
| Permissions | Simple membership role string on tenant | No role→permission mapping, no allow/deny exceptions |
| Visibility | `tenant.status` + draft/published on address | No unified visibility levels on content |
| Public API | `GET /congregations` lists published tenants | No hierarchical URL resolution |
| Frontend | `/congregations/:id/edit` (authenticated) | No public `/polska/warszawa/przyce` pages |

Relevant code today:

- Backend: `backend/app/modules/tenants/`, `backend/app/modules/congregations/`
- Frontend: `src/modules/congregations/`, `src/modules/admin/`

## Target architecture

### 1. Organizational hierarchy

```
Community (wspólnota)
└── Region (rejon)
    └── Church (zbór)
        └── Branch (placówka)   # optional; may exist without pastor
```

**Tables (proposed):**

```
communities
- id, name, slug, visibility, created_at

regions
- id, community_id (FK), name, slug, created_at

churches
- id, community_id (FK), region_id (FK, nullable), name, slug, created_at
- legacy_tenant_id (FK, nullable) — migration bridge from tenants

branches
- id, church_id (FK), name, slug, pastor_user_id (nullable), created_at
```

**Migration strategy:**

1. Add new tables alongside existing `tenants`.
2. Backfill: each existing `tenant` → one `church` row (`legacy_tenant_id`).
3. Default community: single CHWZ community (slug `chwz`) until multi-community UI exists.
4. Keep `tenant_id` FK on congregation sub-resources during transition; re-key to `church_id` in a later phase.
5. Deprecate direct `tenant_memberships` once ACL is live.

### 2. ACL — roles vs permissions

Roles describe organizational function; permissions describe what a user may do.

```
function/role → default permissions → user exceptions → final permissions
```

**Tables (proposed):**

```
roles
- id, name, scope_type (community|region|church|branch)

role_permissions
- role_id, permission (string enum)

user_role_assignments
- user_id, role_id, scope_id (polymorphic: community/region/church/branch)

user_permissions
- user_id, scope_type, scope_id, permission, effect (allow|deny)
```

**Permission resolution (runtime):**

1. Collect permissions from all `user_role_assignments` matching the resource scope (walk up hierarchy: branch → church → region → community).
2. Apply `user_permissions` exceptions (`deny` wins over `allow`).
3. Check global admin override (`users.role` = admin/owner).

**Initial permission set (MVP):**

| Permission | Description |
|------------|-------------|
| `church.view` | See church profile (respecting visibility) |
| `church.edit` | Edit church profile |
| `church.create` | Create new church |
| `church.move_region` | Move church between regions |
| `church.change_pastor` | Assign/change pastor |
| `people.manage` | Manage contact persons |
| `events.manage` | Manage events (future) |
| `documents.manage` | Manage documents (future) |
| `branch.manage` | Manage assigned branch |

**Default role mappings (MVP):**

| Role | Scope | Default permissions |
|------|-------|---------------------|
| Admin | global | all |
| Bishop | community | all churches in community |
| Regional Bishop | region | churches in region |
| Pastor | church | `church.edit`, `people.manage`, `events.manage` |
| Diacon | church | subset via configuration |
| Branch responsible | branch | `branch.manage` |

Open decisions (for review):

- Who can create churches? (Bishop / Regional Bishop / Admin only?)
- Who can change pastor? (Bishop / Regional Bishop?)
- Who can move church between regions?

### 3. Visibility (read access)

Unified visibility enum for churches, service times, people, documents, events:

```
hidden | public | authenticated | pastors
```

| Level | Who sees it |
|-------|-------------|
| `public` | Everyone (including guests) |
| `authenticated` | Logged-in users |
| `pastors` | Users with pastor-level access in scope |
| `hidden` | Editors only |

Visibility is evaluated **before** edit permission checks on read endpoints.

Add `visibility` column to:

- `churches` (profile-level default)
- `congregation_contact_persons` (replaces/is_public flag from ROADMAP)
- `congregation_service_times`
- future: events, documents

Communities default to `hidden` until explicitly published.

### 4. URL and routing

**Canonical church URL:**

```
/{country_slug}/{city_slug}/{church_slug}
```

Example: `/polska/warszawa/przyce`

- `church_slug` is stable (not derived from street name).
- Country/city slugs come from primary address (normalized, diacritics stripped).

**Aggregate / alias routes:**

| Path | Behavior |
|------|----------|
| `/polska` | List/filter churches in Poland |
| `/polska/warszawa` | Churches in Warsaw |
| `/warszawa` | Alias — same as above if unambiguous; else picker |

**Resolution logic:**

1. Parse path segments.
2. Query churches by country + city + slug.
3. **0 results** → 404 or suggestions page.
4. **1 result** → redirect or render church public page.
5. **N results** → render list/cards picker.

**Backend:**

- `GET /public/churches/resolve?path=polska/warszawa/przyce`
- `GET /public/churches?country=polska&city=warszawa`

**Frontend routes (new module or extend congregations):**

```
/:country/:city/:churchSlug   → PublicChurchPage
/:country/:city               → ChurchListPage
/:country                     → ChurchListPage
/:cityAlias                   → ChurchListPage (alias resolver)
```

Keep existing `/congregations/:id/edit` for authenticated editing during transition.

### 5. Editing permission hierarchy (product rules)

From church-platform source — editorial scope:

```
Admin
├── Bishop          → all churches in community
├── Regional Bishop → churches in assigned region
└── Pastor          → own church (+ branches per ACL)
```

These map to `user_role_assignments` scope, not to URL structure.

## Implementation phases

### Phase 0 — Design review (no code)

- [ ] Confirm terminology: tenant → church migration path
- [ ] Confirm MVP permission set and role defaults
- [ ] Confirm open decisions (create church, change pastor, move region)
- [ ] Canvas diagram of hierarchy + ACL (optional deliverable)

**Issue:** [#006](../issues/2026-07-09--006--org-hierarchy-data-model.md)

### Phase 1 — Data model & migrations

- [ ] Alembic migrations: `communities`, `regions`, `churches`, `branches`
- [ ] Backfill script: tenants → churches
- [ ] Add `slug`, `visibility` to church-level entities
- [ ] Repository layer + basic CRUD (admin-only initially)

**Issues:** [#006](../issues/2026-07-09--006--org-hierarchy-data-model.md), [#007](../issues/2026-07-09--007--acl-roles-permissions.md)

### Phase 2 — ACL engine

- [ ] Tables: `roles`, `role_permissions`, `user_role_assignments`, `user_permissions`
- [ ] `PermissionService.resolve(user, permission, scope)` 
- [ ] FastAPI dependency: `RequirePermission("church.edit", church_id)`
- [ ] Seed default roles and permissions
- [ ] Replace ad-hoc tenant membership checks on congregation endpoints

**Issue:** [#007](../issues/2026-07-09--007--acl-roles-permissions.md)

### Phase 3 — Visibility layer

- [ ] Add `visibility` enum to churches, contact persons, service times
- [ ] Filter public API responses by visibility + auth state
- [ ] Admin/editor UI to set visibility per field group
- [ ] Align with ROADMAP contact-person `is_public` → `visibility` migration

**Issue:** [#008](../issues/2026-07-09--008--visibility-layer.md)

### Phase 4 — Public URL routing

- [ ] Slug generation service (unique per city, stable on rename)
- [ ] Public resolve endpoint + list/filter endpoints
- [ ] Frontend public pages: church detail, city list, country list
- [ ] Alias handling for `/:city` short paths
- [ ] SEO: canonical URLs, meta tags

**Issue:** [#009](../issues/2026-07-09--009--public-hierarchical-urls.md)

### Phase 5 — Management UI & governance

- [ ] Church create / move region / assign pastor flows with permission gates
- [ ] Multi-community admin (hidden by default)
- [ ] User role assignment UI (admin + bishops)
- [ ] Audit log for permission-sensitive changes (optional MVP+)

**Issue:** [#010](../issues/2026-07-09--010--church-governance-actions.md)

## Testing strategy

**Backend (pytest):**

- Permission resolution: role defaults, deny overrides, scope inheritance
- Visibility filtering: guest vs authenticated vs pastor
- URL resolve: 0/1/N matches, alias paths
- Migration: tenant backfill idempotency

**Frontend (vitest):**

- Route guards with mocked permissions
- Public page renders only `public` visibility content for guests

**E2E (playwright, later):**

- Public browse `/polska/warszawa/{slug}`
- Pastor edits own church, cannot edit other church
- Bishop sees all churches in community

## Out of scope (this plan)

- Events and documents modules (visibility enum reserved)
- Billing / account limits (see [feature-029](./2026-03-01--feature-029-account-limits.md))
- Map view / geocoding (see [church-addresses](./2025-01-27--church-addresses.md))
- Full removal of `tenants` table (separate deprecation plan)

## Related issues

| ID | Summary |
|----|---------|
| [006](../issues/2026-07-09--006--org-hierarchy-data-model.md) | Organizational hierarchy data model |
| [007](../issues/2026-07-09--007--acl-roles-permissions.md) | ACL roles and permission resolution |
| [008](../issues/2026-07-09--008--visibility-layer.md) | Unified visibility layer |
| [009](../issues/2026-07-09--009--public-hierarchical-urls.md) | Public hierarchical URLs |
| [010](../issues/2026-07-09--010--church-governance-actions.md) | Church governance (create, move, pastor) |

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | Initial plan from church-platform + organization-and-acl sources |
