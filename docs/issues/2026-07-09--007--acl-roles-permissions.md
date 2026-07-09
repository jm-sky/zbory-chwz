# ACL — roles and permission resolution

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 2)  
**Spec:** [2026-07-09--church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md)

## Problem

ACL must reflect **explicitly chosen** permissions when creating account — not auto-derived from służba.

## Scope

- [ ] ACL tables + `source_assignment_id`
- [ ] `ServiceAssignmentService`: save assignment; if account checked, apply **UI-selected** roles/permissions
- [ ] `suggested_role_id` on `service_types` — prefill only
- [ ] Pastor: inactive account default; ACL from user selection applies before activation
- [ ] Delete assignment → remove ACL rows with matching `source_assignment_id` only
- [ ] `services.manage`, governance endpoints, tests

## Key rule

> Służba ≠ uprawnienia. Przykład: Diakon + opis Skarbnik + konto + wybrane permissiony (np. finanse w przyszłości).

## Decisions (2026-07-09)

- Independent permission pick at account creation
- Pastor ACL before `is_active`

## Open questions

- MVP permission picker: roles only, or roles + individual permissions?
- `finances.manage` — Phase 2 or later?
