# Issue 025 — Eksport zborów JSON/Markdown + filtry (kraj, województwo, placówki)

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `8c11aec`  
**Component:** `CongregationExportMenu.vue`, `useCongregationExport.ts`, `CongregationFilters.vue`  
**Z tego samego promptu:** [#026](./2026-07-10--026--country-iso-province-normalization.md), [#022](./2026-07-09--022--congregation-list-search.md)

## Prompt (Claude Code)

> Chce export zborow do json i markdown, raczej wszystkie na raz  
> Ale mozemy od razu dodac lepsze filtry i eksportowac odfiltrowane.  
> Np. wg kraju, wojewodztwa, bez placowek itp. i full text search

*(sesja `4708d073`)*

## Decyzja

- **Formaty:** JSON (pełna struktura) + Markdown (czytelny raport)
- **Zakres:** domyślnie wszystkie z filtrów listy; nie osobny „export all” poza UI
- **Filtry eksportu:** kraj, województwo (`province`), wykluczenie placówek (`branches`), wyszukiwanie tekstowe
- **FTS:** prosty search w filtrach; dedykowany Postgres tsvector → [#011](./2026-07-09--011--postgres-full-text-search.md)

## Implementacja

- Commit `8c11aec` — `feat(congregations): export to JSON/Markdown with country, province and branch filters`
- `CongregationFilters.vue` — rozszerzone filtry

## Weryfikacja

- Export z aktywnymi filtrami → plik zawiera tylko pasujące zbiory
- JSON i MD poprawnie kodują polskie znaki

## Notes

Kolejny prompt w tej sesji: kraj jako **ISO 3166-1 alpha-2** (`PL`) — [#026](./2026-07-10--026--country-iso-province-normalization.md).
