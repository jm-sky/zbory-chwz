# Grupy ludzi — struktury organizacyjne poza zborami

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--people-groups.md](../plans/2026-07-09--people-groups.md)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)

## Problem

Potrzebujemy definiować **grupy ludzi** niezależne od pojedynczego zboru, np.:

- Prezydium Rady Naczelnej
- Grupa Ewangelizacji
- Służba Więzienna

Grupy służą do organizacji pracy, komunikacji wewnętrznej i (w przyszłości) list mailingowych — bez mieszania z przypisaniami służby w zborze.

## Scope (faza 1 — planowanie)

- [ ] Model: `people_groups`, `people_group_memberships` (FK → `persons`)
- [ ] Zakres grupy: `community` | `region` | `global`
- [ ] CRUD grup + członkostwo (dodaj/usuń osobę)
- [ ] UI: lista grup, edycja członków, opis grupy
- [ ] Uprawnienia: kto może zarządzać grupami (np. Rada Naczelna, admin)

## Poza zakresem fazy 1

- Listy mailingowe — [#015](./2026-07-09--015--mailing-lists.md)
- Automatyczne reguły członkostwa (np. wszyscy pastorzy regionu)

## Acceptance criteria (docelowe)

- Admin może utworzyć grupę z nazwą i opisem
- Do grupy można dodać istniejącą `person` (ta sama tożsamość co w służbach zborowych)
- Osoba może należeć do wielu grup
- Grupa nie zastępuje `service_assignment` w zborze

## Examples

| Grupa | Przykładowi członkowie |
|-------|------------------------|
| Prezydium Rady Naczelnej | Biskup naczelny, wybrani pastorzy |
| Grupa Ewangelizacji | Koordynatorzy ewangelizacji z regionów |
| Służba Więzienna | Osoby prowadzące służbę w więzieniach |
