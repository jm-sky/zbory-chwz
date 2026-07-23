# Issue 022 — Lista zborów — prosta wyszukiwarka

**Data:** 2026-07-09  
**Status:** `done` (2026-07-10)  
**Commit:** `8c11aec` (razem z [#025](./2026-07-10--025--congregation-export-json-markdown-filters.md), [#026](./2026-07-10--026--country-iso-province-normalization.md))  
**Component:** `CongregationFilters.vue`

## Prompt (Cursor)

> Trzdba dodac wyszukiwarke na gorze listy zborow. Prosty search na razie.

*(sesja `79ba874d`)*

## Decyzja

Na landing page listy zborów **prosty filtr tekstowy** po nazwie/mieście (client-side lub query param — w zależności od implementacji). Pełny PostgreSQL FTS → [#011](./2026-07-09--011--postgres-full-text-search.md) (późniejsza faza).

## Implementacja

- `CongregationFilters.vue` — `SearchInput` z `v-model search`
- Integracja z listą zborów (filtrowanie wyników)

## Weryfikacja

- Pole search nad listą, placeholder PL/EN
- Wpisanie fragmentu nazwy zawęża widoczne karty

## Notes

W tej samej sesji użytkownik zapytał o widoczność „Tylko pastorzy” dla admina na karcie — **do zaplanowania** w [#008](./2026-07-09--008--visibility-layer.md) (admin nie widzi danych restricted bez uprawnienia pastora/biskupa).
