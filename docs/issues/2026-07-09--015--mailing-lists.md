# Listy mailingowe

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--mailing-lists.md](../plans/2026-07-09--mailing-lists.md)  
**Depends on:** [#012](./2026-07-09--012--unify-services-remove-contact-persons.md), [#014](./2026-07-09--014--people-groups.md)

## Problem

Potrzebujemy w przyszłości **list mailingowych** do komunikacji wewnętrznej CHWZ (newslettery, ogłoszenia dla grup, zaproszenia). Na razie tylko planowanie — bez implementacji w MVP platformy zborów.

## Zakres docelowy (high level)

- [ ] Listy statyczne i dynamiczne (oparte o grupy ludzi #014)
- [ ] Źródła adresów: `persons.email` z poszanowaniem widoczności i zgód
- [ ] Integracja z dostawcą e-mail (SMTP / SendGrid / …) — TBD
- [ ] Opt-out / zgoda RODO
- [ ] Podgląd odbiorców przed wysyłką

## Poza zakresem (teraz)

- Wysyłka masowa w MVP
- Szablony HTML newsletterów

## Powiązania

- Grupy ludzi ([#014](./2026-07-09--014--people-groups.md)) jako naturalne źródło segmentów
- Widoczność pól e-mail ([#012](./2026-07-09--012--unify-services-remove-contact-persons.md)) — tylko adresy z prawem do kontaktu

## Acceptance criteria (gdy implementacja)

- Administrator grupy może utworzyć listę powiązaną z grupą
- Wysyłka testowa do wybranych odbiorców
- Audyt: kto wysłał, kiedy, do ilu osób
