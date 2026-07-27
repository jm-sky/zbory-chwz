# Church platform — implementation plan

**Status:** `planned`  
**Created:** 2026-07-09  
**Sources:**
- [2026-07-09--church-platform.md](./2026-07-09--church-platform.md) — model zborów, widoczność, URL
- [2026-07-09--organization-and-acl.md](./2026-07-09--organization-and-acl.md) — hierarchia organizacyjna i ACL
- [2026-07-09--church-people-and-services.md](./2026-07-09--church-people-and-services.md) — osoby, służby, konto, uprawnienia

> **Note:** Reviewed 2026-07-09 — see [Design review](#design-review-2026-07-09) for gaps, risks, and suggestions.

> **Aktualizacja 2026-07-25:** dla **Fazy 2 (ACL)** i **Fazy 3 (widoczność)** źródłem prawdy jest
> [acl-architecture.md](./2026-07-25--acl-architecture.md) — rozstrzyga algorytm rozwiązywania
> uprawnień, reguły nadawania ról, `user_permissions` i migrację `tenant_memberships` → ACL.
> Rozbicie na zadania: [acl-implementation-tasks.md](./2026-07-25--acl-implementation-tasks.md).
> Sekcja „2. Służby, People i ACL" poniżej opisuje stan zamierzeń z 2026-07-09 i została w tych
> punktach zastąpiona.

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
└── Region (rejon)              # bishop's jurisdiction — NOT a city/location bucket
    └── Church (zbór)
        └── Branch (placówka)   # optional; may exist without pastor
```

#### Region — bishop's jurisdiction (not a city)

**Region** describes the **scope of a regional bishop's work** (zasięg pracy biskupa), not a geographic alias for a city. A city belongs to a region; URL routing (`/polska/warszawa/...`) uses **address city**, independent of region assignment.

**CHWZ regions (seed data):**

| Region | Regional bishop | Example churches / cities |
|--------|-----------------|---------------------------|
| Dolny Śląsk | — *(fallback: biskup naczelny)* | — |
| Górny Śląsk | Andrzej Poręba (Zabrze) | Zabrze, … |
| Północno-Wschodni | Jacek Romanowski | Gdańsk, Gołdap, Bydgoszcz, Kętrzyn, Białystok |
| Centralny | Leszek Bijak | Warszawa, Łódź |

**Biskup naczelny (community scope):** Roman Jawdyk — role `Bishop`, scope = community CHWZ.

**Fallback:** Region without `biskup_regionu` assignment → biskup naczelny inherits regional permissions (`church.create`, `services.manage` in that region).

A church has one `region_id`; moving between regions is a governance action (bishop only — see §5).

**Tables (proposed):**

```
communities
- id, name, slug, visibility, created_at

regions
- id, community_id (FK), name, slug, created_at

churches
- id, community_id (FK), region_id (FK, nullable), tenant_id (FK)
- name, visibility, created_at
- (canonical URL slugs live on church_slug_aliases — see below)

church_slug_aliases
- id, church_id (FK)
- alias_type: canonical | street | custom_name | short_name | legacy
- country_slug, city_slug, slug
- is_canonical (bool) — one canonical alias per church (primary public URL)
- created_at
- UNIQUE (country_slug, city_slug, slug)

city_aliases
- id, country_slug, alias_slug, city_slug
- created_at
- UNIQUE (country_slug, alias_slug)

branches
- id, church_id (FK), name, slug, visibility, created_at

persons
- id, first_name, last_name, email, phone (all nullable)
- user_id (FK → users, nullable)
- created_at, updated_at

service_types
- id, slug, name, scope_type (community|region|church|branch)
- suggested_role_id (FK → roles) — podpowiedź UI, **nie** auto-ACL
- is_senior_tier (bool)
- sort_order, is_system
- probation_supported (bool) — poza MVP

service_assignments
- id, person_id (FK)
- scope_type, scope_id (community|region|church|branch)
- service_type_id (FK, nullable — gdy „Inna”)
- custom_service_name (nullable)
- description (nullable)
- started_at, ended_at (nullable), created_at
- probation_ends_at (nullable) — poza MVP
```

Szczegóły UX i reguł konta: **[church-people-and-services.md](./2026-07-09--church-people-and-services.md)**.

**Wstępna lista `service_types` (seed):** biskup naczelny, biskup senior, biskup regionu, biskup, pastor, młodszy pastor, senior pastor, diakon, senior diakon, lider młodzieżowy + opcja **„Inna”** w UI (`custom_service_name`).

| slug | `suggested_role_id` |
|------|---------------------|
| `lider_mlodziezowy` | **brak** (`NULL`) — tylko służba organizacyjna; ACL wyłącznie jeśli ręcznie wybrane przy „Utwórz konto” |
| pozostałe seed | podpowiedź roli wg mapowania (Bishop, Pastor, Diacon, …) |

**Senior:** osobny typ służby (`senior_pastor`, …); wielu w zborze dozwolonych.

**Osoba ≠ user:** ta sama `person` w wielu zborach; konto opcjonalne; uprawnienia **niezależne** od służby (podpowiedź z `suggested_role_id`).

#### Tenants (backward compatibility)

Keep the `tenants` table and `tenant_id` FKs for backward compatibility with existing code and congregation sub-resources. **Operationally there is always a single organizational tenant** (CHWZ) on this deployment — no multi-org tenants in practice.

**Target model (confirmed):**

```
tenants (1 row: CHWZ org)
└── churches (N rows, each church.tenant_id → CHWZ tenant)
    └── congregation_* rows gain church_id FK (tenant_id stays, same value for all)
```

- `churches.tenant_id` → FK to the single CHWZ tenant row (all churches share it).
- Add `church_id` (FK, NOT NULL after backfill) on `congregation_addresses`, `congregation_service_times`, `congregation_contact_persons` — **required** because `tenant_id` alone no longer identifies a congregation.
- Do **not** remove `tenants` or `tenant_memberships` in this plan — ACL replaces ad-hoc role checks, but tenant infrastructure stays.
- Existing API paths `/{tenant_id}/...` remain during transition; resolve `tenant_id` ↔ `church_id` via `churches` table (1:1 after migration).

**Migration strategy (Phase 1):**

1. Create CHWZ org tenant row (or designate existing one).
2. Add hierarchy tables (`communities`, `regions`, `churches`, `branches`).
3. For each existing congregation tenant: create `church` row with `tenant_id` = CHWZ org tenant; store mapping `old_tenant_id → church_id` in migration table or `churches.id` = former tenant id (simplest: reuse UUID).
4. Add `church_id` to congregation sub-tables; backfill from mapping.
5. Seed default community (`chwz`) and four regions (table above).
6. Deprecate `POST /tenants` for congregation creation — governance flow creates `church` instead (Phase 5).

**DB constraints (add in migration):**

| Table | Constraint |
|-------|------------|
| `regions` | `UNIQUE (community_id, slug)` |
| `churches` | `UNIQUE (community_id, slug)`; `region_id` FK **nullable** (admin/biskup uzupełnia później) |
| `branches` | `UNIQUE (church_id, slug)` |
| `churches` | index on `(tenant_id)`; index on `(region_id)` |
| `church_slug_aliases` | `UNIQUE (country_slug, city_slug, slug)`; one `is_canonical` per church |
| `city_aliases` | `UNIQUE (country_slug, alias_slug)` |
| `service_types` | `UNIQUE (slug)` |
| `persons` | index on `(email)` where not null |

### 2. Służby, People i ACL

**Służba** = funkcja organizacyjna. **Uprawnienia** = osobna warstwa — wybór przy tworzeniu konta, nie sztywny mapping z służby.

```
person → service_assignment (służba + opis)
              └── opcjonalnie: user + wybrane role/permissions (source_assignment_id)
```

**Tabele ACL:**

```
roles
- id, name, scope_type (community|region|church|branch)

role_permissions
- role_id, permission (string enum)

user_role_assignments
- user_id, role_id, scope_id, source_assignment_id (FK → service_assignments, nullable)

user_permissions
- user_id, scope_type, scope_id, permission, effect (allow|deny)
```

`source_assignment_id` — śledzi, które przypisanie służby wygenerowało rolę (łatwiejsze usuwanie przy odejściu ze służby).

**Permission resolution (runtime):**

1. Zbierz role z `user_role_assignments` (scope: branch → church → region → community).
2. Wyjątki `user_permissions` (`deny` > `allow`).
3. Override admin (`users.is_admin` / owner).

**Zapis przypisania z kontem:**

1. Utwórz/znajdź `person`; opcjonalnie `users` (pastor: `is_active=false` domyślnie).
2. Zapisz `service_assignment`.
3. Jeśli zaznaczono konto: zapisz **wybrane** `user_role_assignments` / `user_permissions` z `source_assignment_id` (UI podpowiada z `suggested_role_id`).
4. Pastor: ACL od razu mimo `is_active=false`.
5. Usunięcie przypisania → usuń tylko ACL z tym `source_assignment_id`.

**Initial permission set (MVP):**

| Permission | Description |
|------------|-------------|
| `church.view` | See church profile (respecting visibility) |
| `church.edit` | Edit church profile |
| `church.create` | Create new church |
| `church.move_region` | Move church between regions |
| `services.manage` | Assign/remove service_assignments (pastor, diakon, …) |
| `people.manage` | Manage contact display / people bez zmiany służb uprzywilejowanych |
| `events.manage` | Manage events (future) |
| `documents.manage` | Manage documents (future) |
| `branch.manage` | Manage assigned branch |

**Default role mappings (MVP):**

| Role | Scope | Default permissions |
|------|-------|---------------------|
| Admin | global | all |
| Bishop | community | all; `church.create`, `church.move_region`, `services.manage` |
| Regional Bishop | region | churches in region; `church.create`, `services.manage` |
| Pastor | church | `church.edit`, `people.manage`, `events.manage` |
| Diacon | church | `church.edit`, `people.manage`, `events.manage`; **no** `services.manage` for pastor/bishop service types; **no** governance |
| Branch responsible | branch | `branch.manage` |

**Governance rules (confirmed):**

| Action | Who may perform it |
|--------|-------------------|
| **Create church** | Bishop (any region), Regional Bishop (own region), Admin |
| **Manage services** (`services.manage`) | Bishop, Regional Bishop (own region), Admin — przypisania pastorów, diakonów, … |
| **Change region** | Bishop only |

Scope enforcement: Regional Bishop permissions apply only to churches where `church.region_id` matches their assignment. Bishop (community scope) is not region-limited.

#### Przypisania — skrót

Pełna specyfikacja: [church-people-and-services.md](./2026-07-09--church-people-and-services.md).

- Wyszukaj istniejącą osobę lub dodaj nową (pola opcjonalne)
- Służba z listy lub „Inna” + `custom_service_name`
- Opis dowolny
- Checkbox konto + **niezależny** wybór uprawnień
- `GET /persons/search` dla wyboru osoby

**API `services.manage`:**

- `GET/POST/PATCH/DELETE .../service-assignments` (scope: church / region / community)
- Walidacja: Diakon nie może przypisać typów `biskup_*`, `pastor`, `*_pastor`
- Biskupi seedowani jako `service_assignments` na community/region (Jawdyk → `biskup_naczelny`, itd.)

#### Bishop assignments (via service_assignments)

| Person | service_type | scope |
|--------|--------------|-------|
| Roman Jawdyk | `biskup_naczelny` | community |
| Leszek Bijak | `biskup_regionu` | Centralny |
| Jacek Romanowski | `biskup_regionu` | Północno-Wschodni |
| Andrzej Poręba | `biskup_regionu` | Górny Śląsk |

Fallback regionu bez `biskup_regionu`: uprawnienia rejonowe jak dla `biskup_naczelny` (PermissionService).

#### Diacon (confirmed)

Diakon może edytować profil zboru i ludzi, **bez** `services.manage` dla służb pasterskich/biskupich i bez governance.

#### Poza MVP

- `probation_ends_at` na `service_assignments` + `probation_supported` na typach służb
- Nadpisywanie domyślnej roli ACL per assignment (poza selectem przy „Dodaj konto”)

#### Permission resolution — implementation notes

- Cache resolved permissions per `(user_id, scope_type, scope_id)` in Redis with TTL (e.g. 5 min); invalidate on role/assignment change.
- `RequirePermission("church.edit", church_id)` walks: branch → church → region → community assignments.
- Global admin: `users.is_admin` or `users.role` in (`admin`, `owner`) — align with existing auth model.

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

**Who qualifies for `pastors` visibility level:**

Użytkownicy z aktywną służbą mapowaną na role **Bishop / Regional Bishop / Pastor / Diacon** (przez `service_assignments` + ACL). Branch responsible i zwykły user bez służby — **nie**.

> Nazwa enum `pastors` jest historyczna — obejmuje też biskupów i diakonów.

**Migration from current status fields:**

| Current (`tenant.status` / `address.status`) | Target `visibility` |
|---------------------------------------------|---------------------|
| `draft`, `need_verification` | `hidden` |
| `published`, `published_unverified` | `public` (church profile); sub-entities keep own visibility, default `public` for service times, `authenticated` for contact persons until reviewed |

Keep `address.status` for editorial workflow (`need_verification`) separate from visibility — a church can be `visibility = public` but address still `need_verification` for internal QA. Document in issue #008.

**Church-level publish gate:** public URL returns 404 unless `churches.visibility` in (`public`) AND primary address exists. Sub-entity visibility filters content on the page.

### 4. URL and routing

**Canonical church URL** (from `church_slug_aliases` where `is_canonical = true`):

```
/{country_slug}/{city_slug}/{slug}
```

Example: `/polska/warszawa/przyce`

**Church aliases (1+ per church):**

| `alias_type` | Przykład | Użycie |
|--------------|----------|--------|
| `canonical` | `przyce` | Główny URL |
| `street` | `ul-przyce-21` | Ulica |
| `custom_name` | `genezaret` | Nazwa własna |
| `short_name` | `wawa-i` | Skrót |
| `legacy` | alias po zmianie miasta | 301 → canonical |

Wszystkie aliasy: unikalne `(country_slug, city_slug, slug)`; resolve trafia w dowolny alias → ta sama strona zboru.

**City aliases** — skróty typu `/:warszawa` (tabela `city_aliases`); wymagane na MVP.

**Zmiana miasta** (np. Żory → Rybnik):

1. Zaktualizować `city_slug` na canonical alias (nowy URL).
2. Dodać alias `legacy` ze starym miastem (`polska/zory/...`).
3. HTTP **301** ze starych ścieżek na canonical.
4. Opcjonalnie: wpis w `city_aliases` jeśli zmienia się też skrót miasta.

**Slug normalization rules:**

- Lowercase ASCII; strip Polish diacritics (`ł` → `l`, `ś` → `s`, …).
- Spaces → hyphens; collapse repeated hyphens.
- `country_slug`: from `address.country` (`Poland` → `polska`).
- `city_slug`: from `address.city` (`Warszawa` → `warszawa`).
- `church_slug` segment: from alias type on create; **canonical** slug stable unless bishop/admin rename.
- `city_slug` **may change** when primary address city changes (with legacy alias + 301).
- Uniqueness: `(country_slug, city_slug, slug)` on `church_slug_aliases`.

**Aggregate / alias routes:**

| Path | Behavior |
|------|----------|
| `/polska` | List/filter churches in Poland |
| `/polska/warszawa` | Churches in Warsaw |
| `/warszawa` | City alias — **required MVP**; picker if ambiguous |

**Resolution logic:**

1. Parse path segments.
2. Try match: `city_aliases` (1 segment) → `country+city` (2) → `country+city+slug` (3) against `church_slug_aliases`.
3. Legacy alias hit → **301** to canonical URL.
4. **0 results** → 404 or suggestions.
5. **1 result** → church public page.
6. **N results** → list/cards picker.

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

**Route conflict mitigation (frontend):**

Reserved first-segment paths must not hit city alias: `admin`, `auth`, `login`, `register`, `congregations`, `settings`, `dashboard`, `api`, static legal pages (`privacy`, `cookies`, `contact`, …). Register public church routes in `public` layout **before** catch-all `/:cityAlias`. Consider prefix `/z` or `/zbory` if conflicts appear in production.

**API transition:**

| Phase | Public | Authenticated |
|-------|--------|---------------|
| Now | `GET /congregations`, `GET /congregations/detailed` | `GET/PUT /congregations/{tenant_id}/...` |
| Phase 4+ | `GET /public/churches/...` | `GET/PUT /churches/{church_id}/...` (parallel) |
| Later | deprecate tenant-based public list | `tenant_id` param accepted as alias for `church_id` during transition |

### 5. Editing permission hierarchy (product rules)

From church-platform source — editorial scope:

```
Admin
├── Bishop          → all churches in community
├── Regional Bishop → churches in assigned region
└── Pastor          → own church (+ branches per ACL)
```

These map to `user_role_assignments` scope, not to URL structure.

## Design review (2026-07-09)

### Overall assessment

Plan is **directionally sound** and aligned with source docs. Governance rules and region semantics are now clear. Main risks are **tenant migration complexity**, **route collisions**, and **under-specified pastor/visibility edge cases** — addressed in sections above.

### Critical items before Phase 1 coding

| # | Item | Status | Action |
|---|------|--------|--------|
| 1 | Single tenant + `church_id` on sub-resources | ✅ decided | Implement in #006 migration |
| 2 | Służby + `service_assignments` + sync ACL | ✅ decided | Elastyczne typy; senior = osobny typ służby |
| 3 | Slug storage | ✅ decided | `church_slug_aliases` + `city_aliases` |
| 4 | Bishop (community) — Roman Jawdyk | ✅ decided | Seed community Bishop assignment |
| 5 | Regional bishops per region | ✅ decided | Poręba → Górny Śląsk; Dolny Śląsk → fallback naczelny |
| 6 | `church-addresses` plan vs `congregation_addresses` | ⚠️ note | Current code uses `congregation_addresses`; defer multi-address until after MVP |

### Suggestions by area

**Data model**

- Reuse existing tenant UUID as `churches.id` to minimize API/frontend churn (`/congregations/:id/edit` keeps working).
- `region_id` nullable — admin/biskup uzupełnia później.
- **Placówki (branches):** schema + **UI w Phase 1** — zboru w CHWZ już mają placówki.

**ACL**

- Implement `PermissionService` before wiring all endpoints; start with `church.edit` + governance permissions.
- Add integration test matrix: (role × action × in/out of scope) — 15–20 cases cover governance rules.
- Keep `tenant_memberships` read-only mirror during transition; do not dual-write roles indefinitely.

**Visibility**

- Split **workflow status** (`draft` / `need_verification`) from **visibility** — do not overload one enum.
- Public list endpoint: filter `churches.visibility = public`, not `tenant.status`.

**URLs**

- Ship slug columns in Phase 1 even if public routes come in Phase 4 — enables testing and admin preview.
- City alias `/:city` is nice-to-have; defer if router conflicts are painful.

**Phasing**

- Phase 2 (ACL) should include governance **API** endpoints, not only Phase 5 — UI can follow later.
- Phase 0 canvas diagram still useful for bishop/regional bishop/pastor explanation for stakeholders.

### Risk register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration breaks existing edit URLs | High | Reuse church.id = old tenant.id |
| `/:city` catches app routes | High | Reserved path list + route order |
| Permission check latency | Medium | Redis cache + invalidate on assignment change |
| Regional Bishop creates church in wrong region | Medium | Server-side validate `region_id` against user's region assignment |
| Public page leaks `hidden` contact data | High | VisibilityService on every public serializer field |

### Dependency graph

```
Phase 1 (model) ──┬──► Phase 2 (ACL) ──► Phase 5 (governance UI)
                  │         │
                  │         └──► Phase 3 (visibility)
                  │
                  └──────────────► Phase 4 (public URLs) ── depends on visibility for content
```

## Implementation phases

### Status faz (2026-07-25)

| Faza | Status | Uwagi |
|------|--------|-------|
| 0 — Design review | `done` | decyzje potwierdzone; diagram canvas nadal opcjonalny |
| 1 — Model danych i migracje | `done` | dowieziona w [#019](../issues/2026-07-09--019--church-phase-1-hierarchy.md), migracje 056–059; brakuje tylko UI wyszukiwarki osób → [#010](../issues/2026-07-09--010--church-governance-actions.md) |
| 2 — ACL engine | `done` | T1–T9 (`a69366c` 2026-07-25): `PermissionService`, cache, enforcement, governance API. Plan: [acl-implementation-tasks.md](./2026-07-25--acl-implementation-tasks.md) |
| 3 — Widoczność | `done` | T10–T12: publiczna lista po `churches.visibility`, backfill 080 |
| 4 — Publiczne URL-e | `planned` | tabele aliasów i backfill są, brak resolve'a i stron publicznych (#009) |
| 5 — Governance UI | `done` | G0–G13 dowiezione — [governance-ui-tasks.md](./2026-07-27--governance-ui-tasks.md). „Multi-community admin" odłożony (poza zakresem MVP) |

### Phase 0 — Design review (no code)

- [x] Confirm terminology: keep `tenants` + `tenant_id` for backward compat; single CHWZ tenant; churches as hierarchy under community/region
- [x] Confirm region = bishop jurisdiction (not city); four CHWZ regions seeded
- [x] Confirm MVP permission set and role defaults
- [x] Confirm governance: create church (bishop + regional bishop in region + admin), change pastor (+ regional bishop + admin), change region (bishop only)
- [ ] Canvas diagram of hierarchy + ACL (optional deliverable)

**Issue:** [#006](../issues/2026-07-09--006--org-hierarchy-data-model.md)

### Phase 1 — Data model & migrations

- [ ] Alembic: hierarchy + `persons`, `service_types`, `service_assignments`, aliases, `city_aliases`
- [ ] Add `church_id` FK to congregation sub-tables
- [ ] Backfill: single CHWZ tenant + churches (reuse tenant UUID as `churches.id` where possible)
- [ ] Seed community `chwz` + four regions + city aliases + service_types + bishop assignments
- [ ] `GET /persons/search` + CRUD churches, branches, service-assignments, aliases
- [ ] **Frontend:** placówki + Ludzie/Służby — [church-people-and-services.md](./2026-07-09--church-people-and-services.md)
- [ ] CLI seeder: `python -m cli churches backfill` (idempotent)

**Issues:** [#006](../issues/2026-07-09--006--org-hierarchy-data-model.md), [#007](../issues/2026-07-09--007--acl-roles-permissions.md)

### Phase 2 — ACL engine

- [ ] Tables: `roles`, `role_permissions`, `user_role_assignments`, `user_permissions`
- [ ] `PermissionService.resolve(user, permission, scope)` + Redis cache
- [ ] FastAPI dependency: `RequirePermission("church.edit", church_id)`
- [ ] Seed default roles and permissions (incl. governance permissions)
- [ ] `ServiceAssignmentService` — person link, optional account, **explicit** ACL payload from UI
- [ ] Governance API: `POST /churches`, `PATCH .../region`, CRUD `.../service-assignments`
- [ ] Replace ad-hoc tenant membership checks on congregation write endpoints

**Issue:** [#007](../issues/2026-07-09--007--acl-roles-permissions.md)

### Phase 3 — Visibility layer

- [ ] Add `visibility` enum to churches, contact persons, service times
- [ ] Filter public API responses by visibility + auth state
- [ ] Admin/editor UI to set visibility per field group
- [ ] Align with ROADMAP contact-person `is_public` → `visibility` migration

**Issue:** [#008](../issues/2026-07-09--008--visibility-layer.md)

### Phase 4 — Public URL routing

- [ ] Slug service + alias CRUD
- [ ] Resolve endpoint (aliases, legacy 301, city aliases)
- [ ] Frontend public pages + `/:cityAlias` (**MVP**)
- [ ] SEO: canonical URLs, 301 on legacy aliases

**Issue:** [#009](../issues/2026-07-09--009--public-hierarchical-urls.md)

### Phase 5 — Management UI & governance

- [x] Service assignment UI + invite flow for inactive pastor accounts
- [ ] Multi-community admin (hidden by default) — deferred, out of MVP scope
- [x] User role assignment UI (admin + bishops)
- [x] Audit log for permission-sensitive changes

**Issue:** [#010](../issues/2026-07-09--010--church-governance-actions.md) — `done`.
**Plan:** [governance-ui-tasks.md](./2026-07-27--governance-ui-tasks.md) G0–G13.

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
- Removal of `tenants` table (kept for backward compatibility; single tenant per deployment)

## Related issues

| ID | Summary |
|----|---------|
| [006](../issues/2026-07-09--006--org-hierarchy-data-model.md) | Organizational hierarchy data model |
| [007](../issues/2026-07-09--007--acl-roles-permissions.md) | ACL roles and permission resolution |
| [008](../issues/2026-07-09--008--visibility-layer.md) | Unified visibility layer |
| [009](../issues/2026-07-09--009--public-hierarchical-urls.md) | Public hierarchical URLs |
| [010](../issues/2026-07-09--010--church-governance-actions.md) | Church governance (create, move, pastor) |
| [011](../issues/2026-07-09--011--postgres-full-text-search.md) | Full-text search (PostgreSQL) |

**Specs:** [church-people-and-services.md](./2026-07-09--church-people-and-services.md) — osoby, służby, konto, uprawnienia

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | Initial plan from church-platform + organization-and-acl sources |
| 2026-07-09 | Review: region = bishop jurisdiction; keep `tenant_id`; governance rules confirmed |
| 2026-07-09 | Design review: migration details, pastor via ACL, slug rules, risks, phase refinements |
| 2026-07-09 | Bishops: Jawdyk (naczelny), Poręba (Górny Śląsk), fallback naczelny for regions without RB |
| 2026-07-09 | Diacon edit scope; pastors visibility; region nullable; Śląsk = 2 regiony |
| 2026-07-09 | church_pastors table (multi + senior); slug aliases; city change + 301; inactive user invite; branch UI Phase 1 |
| 2026-07-09 | Służby (`service_types` + `service_assignments`); ACL sync; senior = typ służby; pastor ACL przed aktywacją |
| 2026-07-09 | `persons` entity; służba ≠ uprawnienia; „Inna”; wybór istniejącej osoby — [church-people-and-services.md](./2026-07-09--church-people-and-services.md) |
| 2026-07-09 | `lider_mlodziezowy`: brak domyślnej roli ACL (`suggested_role_id` NULL) |
| 2026-07-25 | Status faz zweryfikowany wobec kodu; Faza 2 i 3 przeniesione do [acl-architecture.md](./2026-07-25--acl-architecture.md) + [acl-implementation-tasks.md](./2026-07-25--acl-implementation-tasks.md); ACL jedynym źródłem prawdy (koniec autoryzacji przez `tenant_memberships`) |
| 2026-07-27 | Faza 5 — Governance UI dowieziona (G0–G13: invite flow, ekran nadawania ról, picker wyjątków `user_permissions`, audit log ACL); status `done`. „Multi-community admin" odłożony |
