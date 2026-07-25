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
- **`lider_mlodziezowy`:** `suggested_role_id = NULL` — brak domyślnej roli; tylko służba organizacyjna

## Decisions (2026-07-25)

Pełne uzasadnienia: [acl-architecture.md](../plans/2026-07-25--acl-architecture.md).
Rozbicie na zadania: [acl-implementation-tasks.md](../plans/2026-07-25--acl-implementation-tasks.md) (T1–T9).

- **Picker uprawnień na MVP: tylko role.** Tabela `user_permissions` (allow/deny) wchodzi
  **od razu do modelu i resolvera**, ale UI przy „Utwórz konto” pokazuje wyłącznie wybór roli.
  Wyjątki nadaje admin (na start przez CLI). Dzięki temu późniejsze włączenie wyjątków w UI nie
  wymaga migracji ani przepisania rozwiązywania uprawnień.
- **`finances.manage` — później.** Nie w tej serii; string zarezerwowany, żadna rola go nie dostaje.
  „Diakon-skarbnik” obsługuje na razie sam typ służby (`diakon_skarbnik`).
- **ACL jedynym źródłem prawdy.** `tenant_memberships` przestaje dawać prawo zapisu; zostaje jako
  infrastruktura tenantów. Migracja `owner`/`admin` → rola `pastor` w zasięgu `church`, plus CLI
  `acl migrate-memberships --dry-run` do przejrzenia przed odpaleniem i shadow log po przełączeniu.
- **`deny` wygrywa w całym łańcuchu zasięgów** — nie da się od-blokować węższym `allow`.
  Świadome uproszczenie na rzecz przewidywalności.
- **Fallback biskupa naczelnego nie wymaga kodu** — rola na zasięgu `community` jest przodkiem
  każdego rejonu, więc chodzenie po łańcuchu obsługuje rejon bez `biskup_regionu` samo.
- **Dwa nowe uprawnienia:** `church.view_pastoral` (zastępuje dopasowanie po nazwach ról
  w `AclService.has_pastoral_access`) i `church.publish` (nadane też pastorowi — odpowiada za dane
  własnego zboru; decyzja odwracalna seedem).
- **Nadawanie ról:** zasada podzbioru (nie nadasz uprawnień, których sam nie masz w tym zasięgu)
  + `services.manage` w zasięgu nadania + twarda bramka admin/owner na `bishop` i `regional_bishop`.
  Zastępuje doraźne `can_grant_elevated_roles` z `repositories.py:356`.
- **Diakon nie przypisze służby pasterskiej:** wymagane uprawnienie zależy od
  `service_types.suggested_role` — `bishop`/`regional_bishop` → `services.manage` na `community`,
  `pastor` → `services.manage`, reszta → `people.manage`.

## Stan (2026-07-25)

Zrobione: tabele ACL (migracja 059), seed ról, punktowe bramki na `persons/search` i `POST /tenants`
(commit `8b2f32f`). Brak: `PermissionService`, `user_permissions`, enforcement na zapisach,
governance API.
