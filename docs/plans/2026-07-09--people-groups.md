# Grupy ludzi — plan implementacji

**Status:** `in progress`  
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

## UI (faza 1 — zaimplementowane)

1. **Lista grup** — `/groups` (nie tylko `/admin`, żeby opiekunowie bez roli admina też mieli dostęp)
2. **Szczegóły grupy** — `/groups/:id`: nazwa, opis, widoczność, lista aktywnych członków
3. **Dodaj członka** — formularz (imię, nazwisko, e-mail, telefon, rola w grupie) z wyszukiwarką osób (autocomplete na 4 polach, patrz niżej)

## Ustalenia (2026-07-11) — wyszukiwarka osób (autocomplete) — zaimplementowane

Dotyczy formularza "dodaj osobę" w grupach (`GroupDetailPage`) **oraz** w edytorze zboru (`ChurchPeopleSection` — sekcja "Ludzie i służby"). Cel: unikać duplikatów `persons` przy ręcznym wpisywaniu danych, bez wymuszania wyboru.

1. **Bez osobnego pola combobox.** Każde z 4 istniejących pól (imię, nazwisko, e-mail, telefon) samo działa jak autocomplete — wpisywanie odpytuje wyszukiwarkę osób (debounce) i pokazuje podpowiedzi pod aktywnym polem.
2. **Wybór podpowiedzi** uzupełnia wszystkie 4 pola danymi znalezionej osoby, zapamiętuje jej `personId` i pokazuje badge „Osoba już istnieje" z ikoną odpięcia (✕).
3. **Dalsza edycja dowolnego pola po dopasowaniu automatycznie odpina** `personId` (bo backend przy ustawionym `personId` ignoruje pozostałe pola — pokazywanie edytowanych wartości bez faktycznego ich zapisania byłoby mylące) — z toastem informacyjnym „Edycja możliwa z poziomu przeglądarki osób". Ikona ✕ pozwala odpiąć świadomie, bez edycji.
4. **Wyszukiwarka `GET /churches/persons/search`** rozszerzona o pole `phone` (dziś tylko imię/nazwisko/e-mail) z normalizacją formatowania (spacje/myślniki/nawiasy/`+` ignorowane po obu stronach porównania — wpisanie „600000000” trafia w zapisane „+48 600 000 000”) oraz dopasowanie dwuwyrazowe „imię nazwisko" niezależnie od kolejności słów, żeby wpisanie pełnego imienia i nazwiska trafiało w istniejącą osobę mimo że w bazie są to dwa osobne pola.
5. **`first_name`/`last_name` w modelu `persons` zostają rozdzielone** — rozważano scalenie w jedno pole, odrzucone: dotyka 6 plików backendu i 8 plików frontendu (w tym eksport JSON/Markdown, CLI), traci strukturę (sortowanie po nazwisku, formalne formaty), wymagałoby migracji istniejących danych produkcyjnych. Ten sam efekt UX (wyszukiwanie po pełnym imieniu i nazwisku) osiągnięty przez rozszerzenie zapytania wyszukującego (pkt 4), bez zmiany schematu.
6. **Wspólny kod** — `src/shared/composables/usePersonAutocomplete.ts`, `src/shared/services/personSearchService.ts`, `src/shared/components/PersonSuggestionsList.vue` + `PersonLinkedBadge.vue`, użyte w obu miejscach (grupy i edytor zboru) zamiast kopiowania. Wymagało drobnej poprawki w `ContactFieldWithVisibility.vue` (`inheritAttrs: false` + przekazanie `$attrs` na wewnętrzny input), żeby zdarzenia takie jak `blur` docierały do właściwego pola, a nie do otaczającego kontenera.
7. **Zweryfikowane end-to-end** w przeglądarce (prawdziwy Postgres + Redis): wpisanie fragmentu istniejącej osoby pokazuje podpowiedź, wybór uzupełnia pola i pokazuje badge, dalsza edycja odpina z toastem — w obu miejscach (grupy i edytor zboru).

## Fazy

| Faza | Zakres | Status |
|------|--------|--------|
| 0 | Ten dokument + issue #014 | done |
| 1 | Tabele + CRUD API (migracja `062`, moduł `app/modules/groups`) | done |
| 2 | UI: lista grup, szczegóły, dodawanie/usuwanie członków | done |
| 2b | Wyszukiwarka istniejących `persons` w UI (autocomplete na 4 polach, w grupach i w edytorze zboru) | done |
| 3 | Integracja z listami mailingowymi ([#015](../issues/2026-07-09--015--mailing-lists.md)) | todo |

## Zależności

- `persons` musi istnieć ([#006](../issues/2026-07-09--006--org-hierarchy-data-model.md))
- Spójność z widocznością kontaktów ([#012](../issues/2026-07-09--012--unify-services-remove-contact-persons.md))
