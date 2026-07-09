# Public hierarchical URLs

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 4)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#008](./2026-07-09--008--visibility-layer.md)

## Problem

Congregations are addressed by opaque UUID (`/congregations/:id/edit`). Public discovery needs human-readable, stable URLs like `/polska/warszawa/przyce`.

## Scope

- [ ] Slug service: generate from church name, unique per city, stable across address changes
- [ ] Country/city slugs from primary address (normalized)
- [ ] `GET /public/churches/resolve?path=...` — 0/1/N resolution
- [ ] `GET /public/churches?country=&city=` — list/filter
- [ ] Frontend routes: `/:country/:city/:churchSlug`, list pages, city alias `/:city`
- [ ] Resolution UX: 1 match → church page, N matches → picker, 0 → 404/suggestions
- [ ] Canonical link tags on public church page
- [ ] Keep `/congregations/:id/edit` for authenticated editing

## Acceptance criteria

- `/polska/warszawa/przyce` renders public church profile
- `/warszawa` shows picker when multiple Warsaw churches exist
- Changing street address does not change church URL slug
- Unpublished/hidden churches are not reachable via public URLs

## Notes

- Coordinate with [church-addresses plan](../plans/2025-01-27--church-addresses.md) for primary address + geo fields
