# Model dodawania osób i służb w zborze

**Status:** `confirmed`  
**Created:** 2026-07-09  
**Parent plan:** [2026-07-09--church-platform-implementation.md](./2026-07-09--church-platform-implementation.md)

## Założenie

Przy dodawaniu lub edycji zboru użytkownik zarządza **osobami** i **służbami**. Służba opisuje funkcję organizacyjną; **uprawnienia systemowe są niezależne** od służby.

```
Osoba (person) ──► Przypisanie (service_assignment) ──► Służba + opis
                              │
                              └──► (opcjonalnie) Konto + wybrane uprawnienia ACL
```

## Encja: Osoba (`persons`)

Jedna osoba w systemie może mieć wiele przypisań (różne zboru, różne służby). Tożsamość globalna — nie duplikować przy kolejnym zborze.

```
persons
- id
- first_name, last_name (nullable)
- email, phone (nullable)
- user_id (FK → users, nullable) — gdy ma konto
- created_at, updated_at
```

**Wszystkie pola osoby opcjonalne** — można zapisać samą służbę z minimalnymi danymi.

**Wybór istniejącej osoby:** wyszukiwarka po imieniu, nazwisku, e-mailu (np. pastor już w innym zborze).

## Dodawanie osoby do zboru

### Nowa osoba

Formularz (wszystkie pola opcjonalne):

| Pole | Uwagi |
|------|--------|
| Imię | |
| Nazwisko | |
| E-mail | Wymagany tylko przy „Utwórz konto” |
| Telefon | |

### Istniejąca osoba

- `GET /persons/search?q=` — wybór z listy
- Nowe przypisanie = nowy `service_assignment` dla tej samej `person_id`

## Służba / funkcja

Każde przypisanie (`service_assignment`) ma:

| Pole | Opis |
|------|------|
| **Służba** | Select z listy predefiniowanych `service_types` **lub** „Inna” |
| **Własna nazwa** | Gdy „Inna” — `custom_service_name` (tekst) |
| **Opis** | Doprecyzowanie: „Skarbnik”, „Prowadzi grupę młodzieżową”, … |

Przykłady:

- Służba: `Diakon` · Opis: `Skarbnik`
- Służba: `Inna` · Własna nazwa: `Koordynator techniki` · Opis: `Nagłośnienie i transmisje`

```
service_assignments
- id, person_id (FK)
- scope_type, scope_id (church | branch | region | community)
- service_type_id (FK, nullable gdy „Inna”)
- custom_service_name (nullable)
- description (nullable)
- started_at, ended_at, created_at
```

## Konto użytkownika i uprawnienia

Checkbox: **☐ Utwórz konto użytkownika**

Gdy zaznaczone:

1. Utwórz lub podepnij `users` (`persons.user_id`).
2. **Uprawnienia wybierane niezależnie od służby** — UI może **podpowiedzieć** domyślne (z `service_types.suggested_role_id` lub zestawu permissionów), ale użytkownik decyduje.

Przykład:

| | |
|--|--|
| Osoba | Jan Kowalski |
| Służba | Diakon |
| Opis | Skarbnik |
| Konto | Tak |
| Uprawnienia | `finances.manage` *(przyszłość)* lub wybrane role/permissiony MVP |

Gdy **nie** zaznaczone:

- Osoba widoczna na profilu zboru (wg visibility)
- Brak logowania i brak ACL

### Reguła specjalna: pastor

Dla służb pasterskich (`pastor`, `mlodszy_pastor`, `senior_pastor`):

- Checkbox „Utwórz konto” **domyślnie zaznaczony**
- Konto **`is_active = false`** do momentu zaproszenia
- Wybrane uprawnienia/role ACL **obowiązują od razu** (edycja zboru przed aktywacją logowania)

## Rozdzielenie służba ≠ uprawnienia

| Warstwa | Odpowiada za |
|---------|----------------|
| `service_assignment` | Kim jest w zborze, jaką pełni funkcję (także publiczny profil) |
| `user_role_assignments` / `user_permissions` | Co może w systemie (edycja, governance, finanse, …) |

**Brak automatycznego 1:1** między `service_type` a ACL. `suggested_role_id` na typie służby = tylko podpowiedź w UI.

Powiązanie ACL z przypisaniem: `user_role_assignments.source_assignment_id` — przy usunięciu służby usuwamy ACL utworzone w ramach tego przypisania (nie globalne uprawnienia osoby z innego zboru).

## Cele modelu

- Pastor w wielu zborach (wiele `service_assignment`, jedna `person`)
- Zbór z wieloma osobami i służbami
- Osoba z wieloma służbami (w tym samym lub innym zborze)
- Uprawnienia systemowe nie wynikają sztywno z funkcji kościelnej

## UI (MVP)

Sekcja **Ludzie / Służby** na stronie edycji zboru:

1. Lista przypisań (osoba, służba, opis, konto tak/nie)
2. Dodaj: nowa osoba **lub** wyszukaj istniejącą
3. Służba + opis + opcjonalnie „Inna”
4. Rozwijany panel: konto + wybór uprawnień (z podpowiedzią)
5. Dla pastora: status konta (nieaktywne / zaproszenie wysłane)

## Migracja

- `congregation_contact_persons` → `persons` + `service_assignments` (best-effort map `title` → `service_type`)

## Poza MVP

- `finances.manage` i inne granularne permissiony poza podstawowym zestawem
- Okres próbny na przypisaniu
- Pełna historia `ended_at` w UI

## Related issues

- [#006](../issues/2026-07-09--006--org-hierarchy-data-model.md) — tabele
- [#007](../issues/2026-07-09--007--acl-roles-permissions.md) — ACL
- [#010](../issues/2026-07-09--010--church-governance-actions.md) — UI + invite
