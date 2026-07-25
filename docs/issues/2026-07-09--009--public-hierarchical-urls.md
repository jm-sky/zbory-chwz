# Public hierarchical URLs

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 4)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#008](./2026-07-09--008--visibility-layer.md)

## Problem

Congregations use opaque UUIDs. Public discovery needs human-readable URLs with **multiple aliases** per church and **city shortcuts**.

## Scope

- [ ] Resolve against `church_slug_aliases` + `city_aliases`
- [ ] Alias types: canonical, street, custom_name, short_name, legacy
- [ ] **City alias routes** `/:cityAlias` — **required MVP** (reserved path list)
- [ ] **City change:** update canonical alias; add `legacy` alias; **301** to new URL (e.g. Żory → Rybnik)
- [ ] `GET /public/churches/resolve?path=...`
- [ ] `GET /public/churches?country=&city=&q=`
- [ ] Frontend: `/:country/:city/:slug`, list pages, `/:cityAlias`
- [ ] Canonical `<link rel="canonical">` always points to `is_canonical` alias
- [ ] Keep `/congregations/:id/edit` for authenticated editing

## Resolution order

1. One segment → `city_aliases` → church list or picker
2. Two segments → country + city list
3. Three segments → `church_slug_aliases` match
4. `legacy` type → 301 to canonical URL

## Acceptance criteria

- `/polska/warszawa/przyce` and street/custom aliases resolve to same church
- `/warszawa` works (city alias)
- After city change: old `polska/zory/...` returns 301 to `polska/rybnik/...`
- Hidden churches → 404 on public resolve
- `/admin` not captured by city alias

## Decisions (2026-07-09)

- Multiple aliases per church (street, nazwa własna, skrót)
- `city_slug` may change when address city changes
- City shortcuts required on MVP

## Decisions (2026-07-25)

- **301 dla aliasów `legacy`** — przekierowanie jest trwałe (zbór faktycznie zmienił miasto),
  a 301 przenosi sygnał SEO na nowy URL. 302 zostawiłoby ranking na martwej ścieżce.
- **Alias `short_name` w roocie (`/:short`) — odłożony.** Najpierw warianty w zasięgu miasta;
  root to ta sama przestrzeń nazw co `/:cityAlias`, więc dokładanie tam drugiego typu aliasu
  mnoży kolizje z trasami aplikacji przy zerowym zysku na MVP.

## Stan (2026-07-25) — odłożone

**Blokowane przez [#007](./2026-07-09--007--acl-roles-permissions.md)** (strony publiczne muszą
filtrować treść przez widoczność opartą o `PermissionService`) i przez backfill `churches.visibility`
z [#008](./2026-07-09--008--visibility-layer.md) — bez niego publiczny resolve zwracałby 404 dla
wszystkich zborów.

Zrobione: tabele `church_slug_aliases` i `city_aliases` (migracja 056), `slug_utils.py`, backfill
aliasów kanonicznych. Brak: `GET /public/churches/resolve`, `GET /public/churches`, trasy frontu,
obsługa 301, `<link rel="canonical">`.

## Notes

- FTS (#011) should index alias slugs and church names
- Primary address from `congregation_addresses` drives canonical city_slug on create/update
