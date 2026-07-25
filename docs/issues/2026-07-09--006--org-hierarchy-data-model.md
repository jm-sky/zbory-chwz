# Organizational hierarchy — data model

**Status:** `done` (2026-07-25 — zweryfikowane wobec kodu)  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 1)  
**Spec:** [2026-07-09--church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)

## Scope

- [x] `communities`, `regions`, `churches`, `branches` — `churches/db_models.py`, migracja 056
- [x] `persons` — globalna tożsamość (imię, nazwisko, email, phone — opcjonalne); PII szyfrowane, blind index `email_bidx` / `phone_bidx` (migracja 072)
- [x] `service_types` + `service_assignments` (`custom_service_name` dla „Inna”)
- [x] `church_slug_aliases`, `city_aliases` — tabele + `slug_utils.py` (resolve publiczny → [#009](./2026-07-09--009--public-hierarchical-urls.md))
- [x] `church_id` on congregation sub-tables
- [x] `GET /persons/search?q=` — `churches/router.py:72`, za uprawnieniem `services.manage`
- [x] **Frontend:** placówki + Ludzie/Służby — `ChurchBranchesSection.vue`, `ChurchPeopleSection.vue`
- [x] Backfill: tenants → churches; contact_persons → persons + assignments

## Acceptance criteria

- [x] Ta sama `person` w dwóch zborach (dwa assignments)
- [x] „Inna” służba z `custom_service_name`
- [x] Wszystkie pola osoby opcjonalne przy zapisie
- [x] Branch CRUD + people list on edit page

## Decisions

- See [church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)

## Zamknięcie (2026-07-25)

Model danych dowieziony w [#019](./2026-07-09--019--church-phase-1-hierarchy.md) (commit `18a1a1a`,
migracje 056–059). Weryfikacja wobec kodu 2026-07-25 potwierdza wszystkie pozycje zakresu.

**Zostaje poza tym issue:**

- UI wyboru istniejącej osoby — endpoint jest, żaden komponent go nie woła (P-7 z
  [review](../reviews/2026-07-10--church-platform-review.md)) → [#010](./2026-07-09--010--church-governance-actions.md)
- `churches.region_id` bywa `NULL` (`provisioning.py:68` tworzy zbory bez rejonu) — taki zbór jest
  poza zasięgiem biskupa regionalnego. Uzupełnianie rejonu i walidacja przy tworzeniu →
  [acl-architecture.md §2](../plans/2026-07-25--acl-architecture.md)
