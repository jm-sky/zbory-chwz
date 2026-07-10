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

## Ustalenia (2026-07-10)

1. **Widoczność:** konfigurowalna **per grupa** — pole `visibility` (public / authenticated / private), analogicznie do `card_visibility` w `service_assignments`. Twórca grupy decyduje przy tworzeniu, domyślnie `authenticated`.
2. **ACL:** członkostwo w grupie jest **czysto informacyjne** — nie nadaje żadnych uprawnień w systemie. Uprawnienia nadal wynikają wyłącznie z ról w tenants/service_assignments.
3. **Zarządzanie:** grupy tworzy owner/admin platformy. Owner/admin może wyznaczyć **opiekuna grupy** (`steward_user_id`), który samodzielnie zarządza członkami tej jednej grupy bez potrzeby angażowania admina za każdym razem.

## Model danych (szkic)

```
people_groups
- id
- name                    -- np. "Grupa Ewangelizacji"
- slug
- description (nullable)
- scope_type              -- community | region | global
- scope_id (nullable)     -- FK gdy scope != global
- visibility              -- public | authenticated | private (domyślnie authenticated)
- steward_user_id (nullable) -- FK users, opiekun grupy z prawem zarządzania członkami
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

## Uprawnienia

| Akcja | Kto |
|-------|-----|
| Tworzenie grup (dowolny scope) | Owner, admin platformy |
| Wyznaczenie opiekuna grupy | Owner, admin — przy tworzeniu lub edycji grupy |
| Edycja członków grupy | Owner, admin, oraz `steward_user_id` wyznaczony dla tej grupy |
| Podgląd listy członków | Zależnie od pola `visibility` grupy (public / authenticated / private) |

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
