# Eksport adresów e-mail (filtrowanie + kopiowanie)

**Status:** `planned`
**Created:** 2026-07-09
**Updated:** 2026-07-11 — zakres MVP uproszczony, patrz plan
**Plan:** [2026-07-09--mailing-lists.md](../plans/2026-07-09--mailing-lists.md)
**Depends on:** [#014](./2026-07-09--014--people-groups.md)

## Problem

Administratorzy i pasterze potrzebują szybko zebrać adresy e-mail konkretnej grupy osób (np. „region Północ + pastorzy i diakoni”), żeby wkleić je do zewnętrznego klienta poczty (Gmail, Outlook). Nie potrzebują wysyłki z poziomu aplikacji — to nie jest mailing marketingowy.

## Ustalenia (2026-07-11)

- MVP = filtrowanie + kopiowanie do schowka. Wysyłka, kampanie, szablony — poza zakresem, prawdopodobnie na zawsze.
- Dostęp oparty o istniejący ACL (`user_role_assignments`): `pastor`/`diacon` widzą tylko swój zbór, `regional_bishop` swój region, `bishop` swoją wspólnotę, admin/owner wszystko. Brak roli ACL = brak dostępu.
- Brak zgody/opt-out/audytu wysyłki — aplikacja niczego nie wysyła.
- Brak trwałości — żadnej nowej tabeli, wynik budowany na żądanie.

## Zakres docelowy (high level)

- [ ] Endpoint zwracający osoby z e-mailem, filtrowane po regionie / roli (`service_types`) / grupie (`people_groups`), zawężone do zasięgu ACL wywołującego
- [ ] Strona UI: filtry (multi-select) → tabela wyników → ręczne dodanie/usunięcie osoby → dwa przyciski kopiowania (same adresy `;` / z etykietami `Imię Nazwisko <email>`)
- [ ] Dodanie osoby spoza wyniku przez wyszukiwarkę (`usePersonAutocomplete`, ten sam komponent co w grupach) lub dowolny wolny e-mail

## Poza zakresem (teraz)

- Wysyłka masowa / kampanie / szablony HTML
- Zapisane/nazwane filtry (listy trwałe)
- Zgoda marketingowa / opt-out / audyt wysyłki (nie dotyczy, bo nic nie wysyłamy)

## Powiązania

- Grupy ludzi ([#014](./2026-07-09--014--people-groups.md)) — jeden z wymiarów filtra
- Widoczność pól e-mail ([#012](./2026-07-09--012--unify-services-remove-contact-persons.md)) — świadomie ignorowana w tym narzędziu
- ACL (`roles`/`user_role_assignments`) — źródło ograniczenia dostępu i zasięgu wyników

## Acceptance criteria (gdy implementacja)

- Pastor widzi w eksporcie tylko osoby ze swojego zboru; regional_bishop — swojego regionu; bishop — swojej wspólnoty; admin/owner — wszystkich
- Użytkownik bez żadnej roli ACL dostaje 403 przy próbie użycia narzędzia
- Filtrowanie po regionie + roli + grupie działa łącznie (AND między wymiarami, OR wewnątrz wymiaru)
- Kopiowanie do schowka działa w obu formatach
