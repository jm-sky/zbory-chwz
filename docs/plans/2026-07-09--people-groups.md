# Grupy ludzi — plan implementacji

**Status:** `planned`  
**Created:** 2026-07-09  
**Issue:** [#014](../issues/2026-07-09--014--people-groups.md)  
**Parent:** [2026-07-09--church-platform-implementation.md](./2026-07-09--church-platform-implementation.md)

## Cel

Definiowanie **grup ludzi** w strukturze CHWZ, niezależnych od przypisań służby w konkretnym zborze. Przykłady:

- Prezydium Rady Naczelnej
- Grupa Ewangelizacji
- Służba Więzienna

## Model danych (szkic)

```
people_groups
- id
- name                    -- np. "Grupa Ewangelizacji"
- slug
- description (nullable)
- scope_type              -- community | region | global
- scope_id (nullable)     -- FK gdy scope != global
- created_at, updated_at

people_group_memberships
- id
- group_id (FK)
- person_id (FK → persons)
- role_label (nullable)   -- np. "Przewodniczący" w grupie
- joined_at, left_at (nullable)
```

**Relacja z istniejącym modelem:**

- `persons` — ta sama globalna tożsamość co w `service_assignments`
- Grupa ≠ służba w zborze; osoba może być w obu

## Uprawnienia (szkic)

| Akcja | Kto |
|-------|-----|
| Tworzenie grup community-wide | Owner, admin, uprawnienie `groups.manage` (TBD) |
| Edycja członków grupy regionalnej | Biskup regionu + admin |
| Podgląd listy członków | Zależnie od `visibility` grupy |

## UI (faza 1)

1. **Lista grup** — `/admin/groups` lub sekcja w panelu organizacji
2. **Szczegóły grupy** — nazwa, opis, lista członków
3. **Dodaj członka** — wyszukiwarka `persons` (jak w ChurchPeopleSection)

## Fazy

| Faza | Zakres |
|------|--------|
| 0 | Ten dokument + issue #014 |
| 1 | Tabele + CRUD API |
| 2 | UI admin + wyszukiwarka osób |
| 3 | Integracja z listami mailingowymi ([#015](../issues/2026-07-09--015--mailing-lists.md)) |

## Zależności

- `persons` musi istnieć ([#006](../issues/2026-07-09--006--org-hierarchy-data-model.md))
- Spójność z widocznością kontaktów ([#012](../issues/2026-07-09--012--unify-services-remove-contact-persons.md))

## Open questions

- Czy grupy są widoczne publicznie, czy tylko dla zalogowanych?
- Czy członkostwo w grupie implikuje jakieś uprawnienia ACL?
