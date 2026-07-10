# Issue 034 — Eksport w menu trzech kropek

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `8caaa6f`  
**Component:** `CongregationExportMenu.vue`, `CongregationsList.vue`  
**Related:** [#025](./2026-07-10--025--congregation-export-json-markdown-filters.md)  
**Z tego samego promptu:** [#028](./2026-07-10--028--congregation-create-from-list.md), [#032](./2026-07-10--032--congregation-delete-from-list.md), [#033](./2026-07-10--033--tanstack-query-cache-invalidation.md)

## Prompt (Claude Code)

> 4. Export should be hidden inside three dots dropdown

*(sesja `52a186bf`)*

## Decyzja

Przycisk „Eksport” na wierzchu listy **zaśmiecał** toolbar. Eksport JSON/MD ([#025](./2026-07-10--025--congregation-export-json-markdown-filters.md)) przeniesiony do **DropdownMenu ⋯** obok create/delete.

## Implementacja

- `8caaa6f` — icon-only trigger, eksport w submenu

## Weryfikacja

- Brak osobnego przycisku „Eksport” na liście
- Z menu ⋯: export JSON i Markdown działają z aktywnymi filtrami
