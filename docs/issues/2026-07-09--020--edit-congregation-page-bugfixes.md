# Issue 020 — Strona edycji zboru — błędy przy otwarciu, nawigacja, status

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commits:** `06ef15b`, `cd5ab3b` (częściowo → [#036](./2026-07-09--036--card-visibility-rendering.md))  
**Component:** `EditCongregationPage.vue`, routing  
**Z tego samego promptu:** [#021](./2026-07-09--021--people-services-section-ux.md), [#035](./2026-07-09--035--visibility-enum-acl-tables.md)

## Prompt (Cursor)

> 1. Pojawia sie blad po otwarciu edycji zboru. Zobacz logs.  
> 2. Po wejsciu w edycje i click back button -> strona 404 na url /congregations  
> 3. Zbor ma status "opublikowany" ale po wejsciu w edycje select pokazuje "szkic"  
> 4. Zaznaczenie "utworz konto" przy osobie powinno pokazac select uprawnien  
> 5. Widocznosc email i phone chce miec jako dropdown po prawej stronie input group.

*(sesje `fc3f778c`, `a995af38`)*

| Zgłoszenie | Commit | Issue |
|------------|--------|-------|
| Błąd przy otwarciu edycji | `06ef15b` | ten plik |
| Back → 404 | `06ef15b` (`routes.ts`) | ten plik |
| Status „szkic” vs opublikowany | `06ef15b` | ten plik |
| „Utwórz konto” → select roli | `06ef15b` | ten plik |
| Dropdown widoczności email/tel | `06ef15b`, `cd5ab3b` | [#023](./2026-07-09--023--visibility-picker-icon-only.md), [#036](./2026-07-09--036--card-visibility-rendering.md) |

## Decyzja

- **Back → 404:** ścieżka listy musi być zgodna z `CongregationRoutePaths.list` (env / stała), nie hardcoded `/congregations` jeśli route inny
- **Status draft vs published:** formularz inicjalizuje się z API `status`, nie domyślnym szkicem
- **„Utwórz konto”:** warunkowe pole roli ACL obok checkboxa
- **Widoczność kontaktu:** dropdown z ikoną w input group (nie osobny checkbox) — spójne z [#008](./2026-07-09--008--visibility-layer.md)

## Implementacja

- Commity `06ef15b`, `cd5ab3b`, `0e72878` — `fix(congregations): repair edit page errors and improve people section UX`
- `ContactFieldWithVisibility.vue`, `VisibilityLevelSelect.vue`

## Weryfikacja

- Otwarcie edycji opublikowanego zboru bez błędu w konsoli
- Back wraca na listę (200, nie 404)
- Select statusu = stan z API
