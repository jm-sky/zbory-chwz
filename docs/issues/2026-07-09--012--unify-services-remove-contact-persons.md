# Ujednolicenie ludzi — tylko służby, widoczność na karcie zboru

**Status:** `verification needed`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-assignment-visibility.md](../plans/2026-07-09--church-assignment-visibility.md)  
**Spec:** [2026-07-09--church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#008](./2026-07-09--008--visibility-layer.md)  
**Supersedes:** ROADMAP sekcja „Kontakt osoby - flaga publiczna”

## Problem

Obecnie w UI współistnieją dwie ścieżki:

1. **Osoby kontaktowe** (`congregation_contact_persons`) — osobny formularz na `EditCongregationPage`
2. **Ludzie i służby** (`persons` + `service_assignments`) — `ChurchPeopleSection`

To duplikuje model i myli użytkowników. Wystarczy **jeden model: służba** (przypisanie osoby do funkcji w zborze).

## Decyzja (2026-07-09)

- **Nie** utrzymujemy osobnego modelu „osoba kontaktowa”
- Każda osoba w służbie (`service_assignment`) ma przełącznik widoczności na **publicznej karcie zboru**
- **Telefon** i **e-mail** mają **osobne** przełączniki widoczności (można pokazać osobę, ale ukryć kontakt)
- Domyślnie: osoba widoczna na karcie; telefon publiczny; e-mail domyślnie ukryty

## Scope

- [x] Usunąć sekcję „Osoby kontaktowe” z `EditCongregationPage.vue`
- [x] Rozszerzyć `ChurchPeopleSection` o przełączniki widoczności
- [x] Backend: pola widoczności na `service_assignments` (`show_on_card`, `phone_public`, `email_public`)
- [x] Migracja: `congregation_contact_persons` → `persons` + `service_assignments` (backfill)
- [x] Publiczny widok zboru: kontakt z przypisań służby z uwzględnieniem flag
- [ ] Usunąć / deprecate API `contact_persons` po migracji
- [ ] Migracja boolean → enum widoczności (#008)

## Implementacja (2026-07-09)

- Migracja: `backend/migrations/057_service_assignment_visibility.py`
- Backfill: idempotentny seed `service_types` + migracja contact persons
- Deploy: `python migrations/057_service_assignment_visibility.py upgrade` + `python -m cli db churches-backfill`

## Model widoczności (MVP)

| Pole | Przełącznik | Efekt |
|------|-------------|--------|
| Przypisanie (osoba + służba) | „Widoczne na karcie zboru” | Cały wpis na liście ludzi/służb |
| Telefon | „Telefon widoczny publicznie” | Numer na karcie lub ukryty |
| E-mail | „E-mail widoczny publicznie” | Adres na karcie lub ukryty |

MVP: boolean na `service_assignments`. Docelowo enum z #008: `hidden` | `public` | `authenticated` | `pastors`.

## Acceptance criteria

- [x] Jeden formularz „Ludzie i służby” na edycji zboru
- [x] Osoba ze służbą bez konta może być publiczna lub ukryta na karcie
- [x] Telefon/e-mail mogą być ukryte niezależnie od widoczności imienia i funkcji
- [x] Brak duplikacji danych w UI między `contact_persons` a `service_assignments`
- [x] Dane zmigrowane z istniejących `contact_persons` (backfill)

## Notes

- Służba ≠ uprawnienia systemowe (ACL) — bez zmian, patrz [#007](./2026-07-09--007--acl-roles-permissions.md)
- `title` z contact persons mapuje się na `service_type` + `description`
