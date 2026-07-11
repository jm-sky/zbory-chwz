# Synchronizacja z Google Contacts

**Status:** `planned`
**Created:** 2026-07-10
**Plan:** [2026-07-10--google-contacts-sync.md](../plans/2026-07-10--google-contacts-sync.md)
**Depends on:** [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)

## Problem

Administratorzy zborów prowadzą prywatne książki kontaktów w Google, w których zapisują zarówno całe zbory (jako kontakty-organizacje), jak i osoby powiązane ze służbą. Ręczne przepisywanie tych danych do aplikacji jest czasochłonne i podatne na błędy. Potrzebujemy:

- **importu** (Google → aplikacja) dla adminów/ownerów — zbory i osoby,
- **eksportu** pojedynczych kontaktów (aplikacja → Google) dla dowolnego zalogowanego użytkownika.

## Zakres docelowy (high level)

- [x] Osobne połączenie OAuth „Google Contacts” (inne niż logowanie), z osobnymi scope dla odczytu i zapisu (Faza 1 — write scope przygotowany, nieużyty jeszcze przez export; UI: `/admin/google-contacts`)
- [x] Wczytanie kontaktów użytkownika z filtrem tekstowym „zbór” / „chwz” (nazwa, organizacja, notatki) (Faza 1, backend + frontend)
- [ ] Klasyfikacja kontaktu: zbór vs osoba (heurystyka gotowa i widoczna w UI jako badge; brakuje ręcznej korekty na ekranie mapowania)
- [ ] Ekran mapowania:
  - zbór → auto-dopasowanie po nazwie + potwierdzenie, albo utworzenie nowego zboru
  - osoba → auto-dopasowanie po e-mail/telefon + potwierdzenie, wybór roli (`service_type`) przy dodaniu do zboru, albo tylko poprawa danych osoby globalnej
- [ ] Akcja „Importuj do bazy” (tylko admin/owner) — tworzy/aktualizuje `church` (dla zboru) lub `person` + opcjonalnie `service_assignment` (dla osoby)
- [ ] Akcja „Zapisz / popraw w Google” (dowolny zalogowany) — tworzy/aktualizuje kontakt w Google Contacts użytkownika, ręcznie per kontakt, po zgodzie na dodatkowy (write) scope

## Poza zakresem (teraz)

- Automatyczna, ciągła, dwukierunkowa synchronizacja
- Automatyczne scalanie duplikatów przy nietrafionym dopasowaniu (tylko ręczne potwierdzenie)
- Import z innych providerów (Outlook, Apple Contacts…)

## Powiązania

- [#012](./2026-07-09--012--unify-services-remove-contact-persons.md) — widoczność pól kontaktowych, dotyczy eksportu z kart
- [#014](./2026-07-09--014--people-groups.md) — zaimportowane osoby mogą być później przypisane do grup
- [#018](./2026-07-10--018--congregation-address-data-quality.md), [#026](./2026-07-10--026--country-iso-province-normalization.md) — jakość danych przy tworzeniu nowego zboru z importu

## Acceptance criteria (gdy implementacja)

- Admin/owner może połączyć swoje konto Google (readonly) i wczytać kontakty pasujące do filtra „zbór”/„chwz”
- Ekran mapowania pokazuje proponowaną klasyfikację (zbór/osoba) i proponowane dopasowanie, z możliwością ręcznej korekty przed zapisem
- „Importuj do bazy” tworzy/aktualizuje właściwy rekord (`church`, albo `person`/`service_assignment`) zgodnie z wyborem admina — nigdy automatycznie bez potwierdzenia
- Dowolny zalogowany użytkownik może ręcznie zapisać/zaktualizować pojedynczy kontakt (osobę lub zbór) w swoim Google Contacts, po wyrażeniu zgody na dodatkowy scope zapisu
