# Issue 028 — Tworzenie zboru z listy publicznej

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `8caaa6f`  
**Component:** `CongregationsList.vue`, `congregationApiService.ts`  
**Z tego samego promptu:** [#032](./2026-07-10--032--congregation-delete-from-list.md), [#033](./2026-07-10--033--tanstack-query-cache-invalidation.md), [#034](./2026-07-10--034--export-in-three-dot-menu.md)

## Prompt (Claude Code)

> 3. I see no way to create a new church

*(sesja `52a186bf`)*

## Decyzja

Admin/owner na **publicznej liście zborów** dostaje akcję „Utwórz zbór”. Po utworzeniu **redirect na edycję** — zbór pojawia się publicznie dopiero z opublikowanym adresem (produktowa reguła z commit message).

## Implementacja

- `8caaa6f` — część `feat(congregations): add create/delete actions…`
- `congregationApiService.createCongregation()` + dialog/formularz w `CongregationsList.vue`

## Weryfikacja

- Admin widzi przycisk tworzenia
- Po create → `/congregations/:id/edit`
- Zwykły user nie widzi akcji
