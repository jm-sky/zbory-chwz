# Full-text search (PostgreSQL)

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 4+, po #006)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md) (churches + slugs), opcjonalnie [#009](./2026-07-09--009--public-hierarchical-urls.md)

## Problem

Wyszukiwanie zborów i treści publicznych opiera się dziś na `ILIKE` (`app/common/search.py`) — wolne przy większej liczbie rekordów, słaba jakość dla polskich znaków diakrytycznych i odmian słów.

Publiczna lista (`GET /congregations`) i przyszłe `GET /public/churches?q=` potrzebują szybkiego, jakościowego wyszukiwania po nazwie zboru, mieście, ulicy, opisie.

## Scope

- [ ] Migracja: kolumna `search_vector tsvector` na `churches` (i ewentualnie materialized join z primary address)
- [ ] Trigger lub application-level update: utrzymywać `search_vector` przy INSERT/UPDATE nazwy, slugów, adresu
- [ ] Konfiguracja języka: `simple` + normalizacja polskich znaków **lub** custom config / `unaccent` extension
- [ ] Indeks GIN na `search_vector`
- [ ] `ChurchSearchService` / repository method: `search(query, filters)` z `plainto_tsquery` / `websearch_to_tsquery`
- [ ] Public API: param `q` na `GET /public/churches` i liście miasta/kraju
- [ ] Authenticated admin: search w panelu zborów (`/admin/congregations`)
- [ ] Ranking: `ts_rank` + opcjonalny boost dokładnej nazwy / miasta
- [ ] Testy: polskie znaki (`Wrocław`/`Wroclaw`), partial match, pusty query, XSS w `q` (parametryzowany SQL)

## Proposed `search_vector` sources (MVP)

| Source | Weight |
|--------|--------|
| `churches.name` | A |
| `church_slug_aliases.slug` (all types) | A |
| `church_slug_aliases.city_slug` | B |
| `congregation_addresses.city`, `street` | B |
| `branches.name` | C |

## Acceptance criteria

- `GET /public/churches?q=warszawa` zwraca zboru w Warszawie < 100 ms przy ~100 zborach (lokalnie)
- Zapytanie `przyce` znajduje zbór „Przyce” mimo braku pełnej nazwy
- Wyszukiwanie nie używa string concatenation w SQL — tylko bound parameters
- Istniejący `SearchMixin` / `build_search_filter` pozostaje dla prostych list (users admin); churches używają FTS

## Suggestions

- Rozważyć extension `pg_trgm` jako uzupełnienie FTS dla typo-tolerance (np. `przyce` vs `przyce`).
- Frontend: debounce 300 ms na polu wyszukiwania na landing / liście miasta.
- Nie indeksować pól `visibility = hidden` w wynikach publicznych — filtr po visibility przed/po FTS.
- Issue nie blokuje Phase 1–3; można wdrożyć po public URLs (#009).

## Out of scope

- Elasticsearch / OpenSearch
- Search w dokumentach/wydarzeniach (future modules)
- Highlighting w API (frontend może sam podświetlać)

## Notes

- Obecny kod: `backend/app/common/search.py` (ILIKE) — nie usuwać; FTS to osobna ścieżka dla churches
- Coordinate with ROADMAP public homepage search when defined
- **2026-07-10:** publiczna lista zborów filtruje się w przeglądarce
  (`src/modules/congregations/utils/search.ts` — normalizacja diakrytyków + AND po
  słowach). Przy ~30 zborach to wystarcza i nie blokuje tego issue. FTS staje się
  potrzebne, gdy `GET /congregations/detailed` przestanie zwracać całą listę naraz
  (paginacja) albo gdy dojdzie wyszukiwanie po treściach poza kartą zboru.
