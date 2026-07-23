# Issue 021 — Sekcja Ludzie i służby — UX (widoczność, edycja, etykiety ról)

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commits:** `7585cea`, `06ef15b`  
**Component:** `ChurchPeopleSection.vue`  
**Related:** [#012](./2026-07-09--012--unify-services-remove-contact-persons.md), [#007](./2026-07-09--007--acl-roles-permissions.md)

## Prompt (Cursor)

> Ludzie i sluzby  
> 1. Input group dla email i phone z widocznoscia - nie zawsze rozmiar pasuje...  
> 2. Nie ma guzika/ikony edycji osoby, jest tylko trash.  
> 3. Widocznodc osoby jest jako checkbox a powinien byc dropdown/select zgodnie z dokumentacja - public/only bishops itd.  
> 4. Uprawnienia "Czlonek" to pewnie Member brzmi malo intuicyjnie... Owner - nie wiem skad to.

*(sesja `e67f3236`)*

## Decyzja

- **Widoczność osoby:** enum (`public`, `authenticated`, `pastors`, …) w `Select`, nie boolean checkbox — zgodnie z warstwą widoczności [#008](./2026-07-09--008--visibility-layer.md)
- **Edycja osoby:** ikona Edit obok kosza (inline lub dialog)
- **Input group:** wyrównane wysokości borderów przycisku widoczności i inputu
- **Etykiety ról:** tłumaczenia PL dopasowane do dokumentacji (np. „Brak” zamiast „Członek”; usunięcie mylącego „Owner” z UI służb jeśli to nie rola ACL z planu)

## Implementacja

- Commit `7585cea` — `feat(congregations): unify people/services with card visibility`
- Commit `06ef15b` — poprawki layoutu i formularza

## Weryfikacja

- Select widoczności z etykietami z i18n
- Edycja istniejącej osoby bez usuwania i dodawania od nowa
- Mobile: input group bez „rozjechanych” borderów
