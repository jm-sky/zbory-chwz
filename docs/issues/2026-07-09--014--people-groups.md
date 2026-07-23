# Grupy ludzi — struktury organizacyjne poza zborami

**Status:** `in progress`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--people-groups.md](../plans/2026-07-09--people-groups.md)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)

## Problem

Potrzebujemy definiować **grupy ludzi** niezależne od pojedynczego zboru, np.:

- Prezydium Rady Naczelnej
- Grupa Ewangelizacji
- Służba Więzienna

Grupy służą do organizacji pracy, komunikacji wewnętrznej i (w przyszłości) list mailingowych — bez mieszania z przypisaniami służby w zborze.

## Scope (faza 1 — zaimplementowane)

- [x] Model: `people_groups` (z polami `visibility`, `steward_user_id`), `people_group_memberships` (FK → `persons`) — migracja `062`
- [x] Zakres grupy: `community` | `region` | `global`
- [x] CRUD grup + członkostwo (dodaj/usuń osobę) — `app/modules/groups`, `/api/people-groups`
- [x] UI: lista grup (`/groups`), szczegóły grupy, dodawanie/usuwanie członków
- [x] Uprawnienia: owner/admin tworzy grupy i wyznacza opiekuna (`steward_user_id`); opiekun zarządza członkami swojej grupy

## Ustalenia (2026-07-10)

- **Widoczność:** konfigurowalna per grupa (`visibility`: public / authenticated / private), nie sztywno publiczna ani sztywno tylko-dla-zalogowanych.
- **ACL:** członkostwo w grupie jest czysto informacyjne — **nie** nadaje żadnych uprawnień w systemie.
- **Zarządzanie:** owner/admin + opcjonalny opiekun grupy (`steward_user_id`) zarządzający wyłącznie swoją grupą.

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
