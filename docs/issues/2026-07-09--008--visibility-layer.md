# Unified visibility layer

**Status:** `done` (2026-07-25, commit `a69366c` / PR #32 — T10–T12)  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 3)  
**Depends on:** [#007](./2026-07-09--007--acl-roles-permissions.md)

## Problem

Visibility is inconsistent: `tenant.status`, address `status` (`draft`, `published`, `published_unverified`, `need_verification`), and a planned `is_public` flag on contact persons. Need one mechanism for **read access** separate from edit permissions and separate from **editorial workflow status**.

Current public list (`GET /congregations/detailed`) filters by `address.status in (published, published_unverified)` — must migrate to `churches.visibility`.

## Scope

Backend T10–T12 (2026-07-25) pokrywa enum, `churches.visibility`, backfill i publiczną listę.
Pozostałe checkboxy poniżej = historyczny zakres; deprecjacja `contact_persons` → [#012](./2026-07-09--012--unify-services-remove-contact-persons.md).

- [x] PostgreSQL enum or check constraint: `hidden | public | authenticated | pastors`
- [x] Add `visibility` to `churches`, `service_assignments` (show on card), assignment phone/email
- [ ] Deprecate `congregation_contact_persons` — see [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)
- [x] Migration script — map existing states (migracja 080):

  | Source | Target |
  |--------|--------|
  | `address.status` = `draft` / `need_verification` | church `visibility` = `hidden` |
  | `address.status` = `published` / `published_unverified` | church `visibility` = `public` |
  | service assignments (ex contact persons) | default `public` on card; phone/email per [#012](./2026-07-09--012--unify-services-remove-contact-persons.md) |
  | service times | default `public` |

- [x] Keep `address.status` for workflow (verification queue) — **do not** remove
- [x] `VisibilityService.can_view(level, user, church_scope)` 
- [x] `VisibilityService.filter_fields(serializer, user)` for API responses
- [x] Public endpoints: only `public` content for guests
- [x] Authenticated: `public` + `authenticated`
- [x] `pastors` visibility: users with bishop/pastor/diacon service (via ACL), in scope
- [x] Editor UI: visibility selector na osobach/służbach (`VisibilityLevelSelect` w `ChurchPeopleSection`)
- [x] Communities default to `hidden`

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

## Decisions (2026-07-25)

Kontekst: [acl-architecture.md §10](../plans/2026-07-25--acl-architecture.md) · zadania T10–T12
w [acl-implementation-tasks.md](../plans/2026-07-25--acl-implementation-tasks.md).

- **Backfill `churches.visibility` MUSI poprzedzić przełączenie filtra publicznej listy.**
  Kolumna ma dziś default `hidden` (`churches/db_models.py:59`), a lista publiczna filtruje po
  `tenant.status` (`tenants/repositories.py:48`). Przełączenie filtra bez wcześniejszego backfillu
  **wyczyści publiczny katalog zborów.** Backfill idzie osobną migracją, z liczbami przed i po;
  kryterium akceptacji: liczba zborów `public` == dzisiejsza liczba pozycji w `GET /congregations/detailed`.
- **`pastors` liczone uprawnieniem, nie nazwą roli.** Zamiast `PASTORAL_ROLE_NAMES`
  (`acl_seed.py:11`) — `resolve(user, "church.view_pastoral", church)`. Jedna implementacja
  chodzenia po zasięgach, zestaw uprawnionych zmieniany seedem zamiast edycją kodu.
- **Publikacja za uprawnieniem `church.publish`** (`PATCH /churches/{id}/visibility`), nadanym
  rolom `pastor`, `regional_bishop`, `bishop`.
- **`address.status` zostaje** jako workflow redakcyjny — niezależny od widoczności.

## Stan (2026-07-25)

Zrobione: enum widoczności (`churches/visibility.py`, migracja 058), `VisibilityService`,
widoczność per pole na przypisaniach służb, renderowanie karty zboru wg widoczności
([#036](./2026-07-09--036--card-visibility-rendering.md)), rozróżnienie gość / zalogowany / pastor
w `GET /congregations/detailed` (commit `8b2f32f`, SEC-6).
Brak: filtr publicznej listy po `churches.visibility`, backfill kolumny, endpoint publikacji.
