# Eksport adresów e-mail — plan (MVP: filtrowanie + kopiowanie)

**Status:** `done` (faza 1)
**Created:** 2026-07-09
**Updated:** 2026-07-11 — zakres MVP radykalnie uproszczony po rozmowie planistycznej, faza 1 zaimplementowana i zweryfikowana end-to-end
**Issue:** [#015](../issues/2026-07-09--015--mailing-lists.md)
**Depends on:** [people-groups.md](./2026-07-09--people-groups.md) (done), istniejący ACL (`roles`/`user_role_assignments` w `app/modules/churches`)

## Cel

Szybkie budowanie listy adresów e-mail do wklejenia w zewnętrzny klient poczty (Gmail, Outlook, …) — filtrowanie osób po regionie, roli/służbie i grupie ludzi, **bez wysyłki z poziomu aplikacji**. To nie jest mailing marketingowy, tylko narzędzie do komunikacji wewnętrznej organizacji — stąd brak zgód/opt-out.

## Ustalenia (2026-07-11)

1. **Zakres MVP to wyłącznie budowanie i kopiowanie listy adresów.** Wysyłka (SMTP/ESP), kampanie, szablony HTML — całkowicie poza zakresem; być może nigdy nie będą potrzebne, skoro admin i tak kopiuje adresy do Gmaila.
2. **Dostęp oparty o istniejący ACL, nie o nowe uprawnienie.** Każda osoba z rolą w `user_role_assignments` (`bishop`, `regional_bishop`, `pastor`, `diacon`) widzi w narzędziu tylko osoby w zasięgu **swojej faktycznej roli**: `pastor`/`diacon` → tylko swój zbór (`scope_type='church'`), `regional_bishop` → cały swój region, `bishop` → cała swoja wspólnota. Admin/owner platformy widzą wszystko bez ograniczeń. Brak jakiejkolwiek roli ACL = brak dostępu do narzędzia. (Uwaga: „pastor w zakresie regionu” z pierwotnego opisu nie istnieje w obecnym modelu ACL — zwykły `pastor` jest zawsze zborowy, nie regionalny.)
3. **Filtry: Region + Rola/służba + Grupa.**
   - Region → tabela `regions` (community → region → zbór)
   - Rola/służba → `service_types` przypisane przez `service_assignments` (Pastor, Diakon, …) — **to inne pojęcie niż rola ACL z punktu 2**, mimo tych samych nazw (jedno to „czym się ta osoba zajmuje”, drugie to „do czego ma dostęp w appce”)
   - Grupa → `people_groups` przez `people_group_memberships` (#014)
   - Łączenie: AND między wymiarami, OR wewnątrz wymiaru (multi-select, np. zaznaczenie „Pastor” + „Diakon” = suma obu)
   - Dla użytkownika ograniczonego zasięgiem ACL (punkt 2) filtr regionu/wspólnoty jest zawężony do jego zasięgu, nie do wyboru dowolnego
4. **Wynik:** lista `{imię, nazwisko, e-mail}`, deduplikacja po `person_id` (osoba może pasować kilkoma ścieżkami naraz, np. służbą i grupą). Można ręcznie usunąć wiersz. Można ręcznie dodać: (a) istniejącą osobę przez wyszukiwarkę — ten sam komponent `usePersonAutocomplete` co w grupach, (b) dowolny e-mail spoza systemu (wolne pole tekstowe, bez powiązania z `person`).
5. **`email_visibility` z karty zboru jest świadomie ignorowane.** To wewnętrzne narzędzie adminów/pasterzy — te same osoby i tak widzą te adresy w edytorze zboru; nie ma sensu dodatkowo filtrować.
6. **Kopiowanie do schowka w dwóch formatach:** same adresy rozdzielone `;` (`a@x.pl;b@x.pl`) oraz z etykietami rozdzielone `, ` (`Jan Kowalski <a@x.pl>, ...`).
7. **Brak trwałości.** Nic nie jest zapisywane w bazie — żadnej tabeli `mailing_lists`/`mailing_list_subscribers`. Filtr buduje wynik na żądanie; znika po opuszczeniu strony. Zapisane/nazwane filtry to ewentualna faza 2, nie MVP.
8. **Brak RODO/opt-out/audytu wysyłki.** Aplikacja niczego nie wysyła, więc nie ma czego audytować pod kątem wysyłki — adresy są już widoczne tym samym osobom w innych miejscach systemu. Jedynym realnym ryzykiem jest zbyt szeroki dostęp do narzędzia (patrz Ryzyka).

## Model danych

Brak nowych tabel. Zapytanie łączy istniejące dane: `persons` (adres e-mail) × `service_assignments` (region/zbór przez `scope_type`/`scope_id`, oraz `service_type_id` jako filtr roli) × `people_group_memberships` (filtr grupy, aktywne członkostwo — `left_at IS NULL`).

## API (zaimplementowane)

```
GET /people-directory/filters
  -> { regions: [{id,name}], serviceTypes: [{id,name}], groups: [{id,name}] }
  (zawężone do zasięgu ACL wywołującego)

GET /people-directory/export
  ?regionIds=...&serviceTypeIds=...&groupIds=...
  -> { persons: [{ id, firstName, lastName, email }] }
```

Zwraca tylko osoby z niepustym `email`. Zasięg wyników zawężony po stronie backendu do ról ACL wywołującego (punkt 2) — nie da się tego obejść parametrami zapytania. Region + rola filtrowane **razem na tym samym** `service_assignment` (nie niezależnie) — „Region Północ + Pastor” znaczy „pastor w regionie Północ”, nie „ktoś z przypisaniem gdziekolwiek w Północy ORAZ osobno gdzieś jako pastor”. Grupa to niezależny, dodatkowy warunek AND. Brak roli ACL → `403`.

Moduł: `backend/app/modules/directory/` (`schemas.py`, `repositories.py`, `router.py`), zarejestrowany w `app/api/router.py`.

## UI (zaimplementowane)

Strona `/people-directory`: checkboxy region / rola / grupa (każdy zawężony do zasięgu ACL) → przycisk „Szukaj” → lista wyników z usuwaniem wiersza → „Dodaj osobę” (ten sam `usePersonAutocomplete`/`PersonSuggestionsList` co w grupach) lub „Dodaj dowolny e-mail” → dwa przyciski kopiowania do schowka (same adresy `;` / z etykietami `Imię Nazwisko <email>`). Dostępna z głównej nawigacji dla każdego zalogowanego; brak roli ACL pokazuje przyjazny komunikat zamiast pustej strony.

Moduł: `src/modules/directory/`.

## Fazy

| Faza | Zakres | Status |
|------|--------|--------|
| 0 | Ten dokument + issue #015 | done |
| 1 | Endpoint filtrowania (region + rola + grupa, zasięg ACL) + strona UI + kopiowanie do schowka | done |
| 2 (opcjonalnie, później) | Zapisane/nazwane filtry, wysyłka przez SMTP/ESP, kampanie | nieplanowane |

## Ryzyka

- **Ekspozycja wielu adresów naraz w jednym eksporcie** — dostęp musi być ściśle ograniczony do ról ACL (punkt 2), inaczej to furtka do masowego zbierania adresów przez dowolnego pastora spoza jego zasięgu. Krytyczne, żeby zasięg był egzekwowany po stronie backendu, nie tylko ukryty w UI.
- **Deduplikacja po `person_id`, nie po `email`** — jeśli dwie różne osoby (rekordy `person`) mają ten sam adres e-mail (np. współdzielone konto rodzinne), obie trafią na listę osobno. Akceptowalne dla MVP.
- **„Rola” oznacza dwie różne rzeczy w tym dokumencie** (ACL do dostępu vs `service_type` do filtrowania) — trzeba to jasno rozdzielić w kodzie (różne nazwy pól/zmiennych), żeby nie pomylić uprawnień z filtrem wyników.

## Zweryfikowane (2026-07-11)

- 9 testów integracyjnych (`tests/integration/directory/`): pastor widzi tylko swój zbór, regional_bishop cały swój region (nie sąsiedni), admin wszystko, outsider bez roli ACL dostaje 403, region+rola łączone na tym samym przypisaniu (nie niezależnie), filtr grupy, `/filters` zwraca regiony zawężone do zasięgu
- End-to-end w przeglądarce (prawdziwy Postgres + Redis): filtr „Pastor” poprawnie wyklucza osobę ze służbą „Diakon”, dodanie osoby przez wyszukiwarkę, dodanie dowolnego e-maila, kopiowanie do schowka w formacie `email;email`
- Po drodze naprawiony błąd: checkboxy filtrów nie miały `id`/`for` między `Checkbox` a `Label`, więc kliknięcie w etykietę (a nie dokładnie w mały kwadrat) nie zaznaczało filtra — naprawione przez dodanie powiązania

## Powiązane

- [#014](../issues/2026-07-09--014--people-groups.md) — grupy ludzi, jeden z wymiarów filtra
- [#012](../issues/2026-07-09--012--unify-services-remove-contact-persons.md) — widoczność kontaktu na karcie zboru, świadomie NIE stosowana w tym narzędziu (Ustalenia, punkt 5)
- `roles` / `user_role_assignments` (`app/modules/churches/acl_models.py`) — źródło ograniczenia zasięgu dostępu (Ustalenia, punkt 2)
