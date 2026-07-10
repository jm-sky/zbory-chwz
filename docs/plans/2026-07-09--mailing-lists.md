# Listy mailingowe — plan (późniejsza faza)

**Status:** `planned`  
**Created:** 2026-07-09  
**Issue:** [#015](../issues/2026-07-09--015--mailing-lists.md)  
**Depends on:** [people-groups.md](./2026-07-09--people-groups.md), [church-assignment-visibility.md](./2026-07-09--church-assignment-visibility.md)

## Cel

Komunikacja e-mailowa wewnątrz organizacji CHWZ: ogłoszenia, newslettery, wiadomości do grup (Prezydium, Grupa Ewangelizacji, …). **Nie w scope MVP** platformy zborów — dokumentacja na później.

## Ustalenia (2026-07-10)

**Decyzja:** wysyłka **nie wymaga** osobnej zgody marketingowej (`marketing_consent`) ani wymogu `email_visibility` — każdy adres `persons.email` obecny w bazie może zostać użyty do listy mailingowej. Świadomie zaakceptowane ryzyko RODO (patrz sekcja Ryzyka) — wymaga polityki prywatności informującej użytkowników, że adres e-mail może być użyty do komunikacji wewnętrznej CHWZ.

## Założenia

1. **Źródło adresów:** `persons.email` — bez dodatkowej bramki zgody/widoczności (patrz Ustalenia wyżej)
2. **Segmentacja:** listy statyczne + listy oparte o `people_groups`
3. **Dostawca:** SMTP aplikacji lub zewnętrzny (SendGrid, Brevo, …) — decyzja przy implementacji
4. **Opt-out:** rejestr wypisań, podgląd odbiorców przed wysyłką

## Model danych (szkic)

```
mailing_lists
- id, name, slug, description
- source_type             -- static | group | query
- source_group_id (nullable)
- created_at

mailing_list_subscribers
- id, list_id, person_id (nullable), email
- subscribed_at, unsubscribed_at
- consent_source

mailing_campaigns (opcjonalnie później)
- id, list_id, subject, body_html, sent_at, sent_by
```

## Przepływ (docelowy)

```mermaid
flowchart LR
  Groups[people_groups] --> List[mailing_list]
  Persons[persons.email] --> List
  List --> Preview[Podgląd odbiorców]
  Preview --> Send[Wysyłka]
  Send --> Provider[SMTP / ESP]
```

## Fazy

| Faza | Zakres |
|------|--------|
| 0 | Ten dokument + issue #015 |
| 1 | Listy statyczne, ręczne dodawanie e-maili |
| 2 | Listy z grup ludzi (#014) |
| 3 | Kampanie, szablony, statystyki otwarć (opcjonalnie) |

## Ryzyka

- **Wysyłka bez jawnej zgody odbiorcy** — decyzja (2026-07-10) świadomie akceptuje to ryzyko; wymaga jawnej polityki prywatności i mechanizmu opt-out oraz audytu wysyłek (kto, kiedy, do ilu osób)
- Duplikaty adresów przy łączeniu grup — deduplikacja po `email`
- Widoczność e-maila na karcie zboru (`email_visibility`) jest niezależna od użycia w mailingu wewnętrznym — adres może być ukryty publicznie, a mimo to trafić na listę mailingową

## Powiązane

- [#014](../issues/2026-07-09--014--people-groups.md) — grupy jako segmenty
- [#012](../issues/2026-07-09--012--unify-services-remove-contact-persons.md) — widoczność pól kontaktu
