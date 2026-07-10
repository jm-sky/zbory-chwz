# Issue 019 — Church platform Phase 1 — hierarchia, API, UI placówek i ludzi

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commit:** `18a1a1a`  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md)  
**Related:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#012](./2026-07-09--012--unify-services-remove-contact-persons.md) (`7585cea` — osobny commit tego samego dnia)

## Prompt (Cursor)

> implement  
> *(sesja `acd7e4c2` — po ustaleniach planu platformy kościelnej: regiony biskupów, służby, persons, placówki)*

## Decyzja

Pierwsza faza implementacji modelu organizacyjnego CHWZ:

- **Hierarchia:** `communities` → `regions` → `churches` → `branches` (placówki)
- **Ludzie globalni** (`persons`) + **przypisania służby** (`service_assignments`) zamiast duplikowania kontaktów per zbór
- **Tenant** zostaje dla kompatybilności wstecznej (1:1 ze zbiorem)
- **UI od razu** — sekcje Placówki i Ludzie/Służby na stronie edycji zboru

Szczegóły governance (kto tworzy zbor, zmienia pastora) — w planie; ACL pełne → [#007](./2026-07-09--007--acl-roles-permissions.md).

## Implementacja

- Commit `18a1a1a` — `feat(churches): Phase 1 hierarchy — model, API, branches and people UI`
- Migracje 055–057, backfill `churches-backfill`
- `ChurchBranchesSection.vue`, `ChurchPeopleSection.vue`

## Weryfikacja

- Edycja zboru: dodanie placówki i osoby w służbie
- Ta sama `person` może być w dwóch zborach (dwa assignments)
