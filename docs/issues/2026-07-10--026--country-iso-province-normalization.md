# Issue 026 — Normalizacja kraju (ISO) i województw w adresach

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `8c11aec` (ta sama zmiana co [#025](./2026-07-10--025--congregation-export-json-markdown-filters.md))  
**Related:** [#025](./2026-07-10--025--congregation-export-json-markdown-filters.md), [#018](./2026-07-10--018--congregation-address-data-quality.md)

## Prompt (Claude Code)

> Go on. Kraj lepiej dać jako PL, bedzie miedzynarodowo bez translacji. Warto dac liste krajow, nie dowolny tekst.

*(sesja `4708d073`)*

## Decyzja

- **`country`** w bazie jako **ISO 3166-1 alpha-2** (`PL`, `DE`), nie pełna nazwa — UI tłumaczy przez `geo.py` / i18n
- **Select krajów** z listy, nie free text — zapobiega „Polska” vs „PL» vs „poland»
- **`province`** jako slug ASCII (`lubuskie`, `dolnoslaskie`) — filtrowanie i eksport spójne
- Migracja backfill z scrape `chwz.info.pl`; **2 rekordy** celowo pominięte → [#018](./2026-07-10--018--congregation-address-data-quality.md)

## Implementacja

- Migracja `061_normalize_country_and_province.py`
- `backend/app/modules/congregations/geo.py`
- Frontend: lista krajów w filtrach i formularzu

## Weryfikacja

- Filtr kraju `PL` działa w liście i eksporcie
- Zbiory z `province IS NULL` widoczne na liście, ale poza filtrem województwa
