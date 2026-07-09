# Organizational hierarchy — data model

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 1)  
**Spec:** [2026-07-09--church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)

## Scope

- [ ] `communities`, `regions`, `churches`, `branches`
- [ ] `persons` — globalna tożsamość (imię, nazwisko, email, phone — opcjonalne)
- [ ] `service_types` + `service_assignments` (`custom_service_name` dla „Inna”)
- [ ] `church_slug_aliases`, `city_aliases`
- [ ] `church_id` on congregation sub-tables
- [ ] `GET /persons/search?q=` — wybór istniejącej osoby
- [ ] **Frontend:** placówki + Ludzie/Służby (formularz wg spec)
- [x] Backfill: tenants → churches; contact_persons → persons + assignments

## Acceptance criteria

- Ta sama `person` w dwóch zborach (dwa assignments)
- „Inna” służba z `custom_service_name`
- Wszystkie pola osoby opcjonalne przy zapisie
- Branch CRUD + people list on edit page

## Decisions

- See [church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)
