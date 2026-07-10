# Issue 035 — Widoczność służby jako enum + tabele ACL

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commit:** `0e72878`  
**Related:** [#008](./2026-07-09--008--visibility-layer.md), [#021](./2026-07-09--021--people-services-section-ux.md)

## Prompt (Cursor)

> Popraw zgodnie z planem.

*(follow-up do sesji `e67f3236` — Ludzie i służby, widoczność jako select nie checkbox)*

## Decyzja

- Migracja **boolean → enum** widoczności na `service_assignments` (`058_service_assignment_visibility_enum.py`)
- Szkielet **ACL** (`059_acl_tables.py`, `acl_service.py`) pod role z planu [#007](./2026-07-09--007--acl-roles-permissions.md)
- Moduł `churches/visibility.py` — filtrowanie pól wg poziomu widoczności odbiorcy

## Implementacja

- `0e72878` — `fixes` (backend migrations 058, 059 + visibility layer)

## Weryfikacja

- `ChurchPeopleSection` zapisuje enum, nie checkbox
- Testy `test_visibility.py` przechodzą
