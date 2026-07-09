# Widoczność przypisań służby na karcie zboru

**Status:** `done` (MVP)  
**Created:** 2026-07-09  
**Parent:** [2026-07-09--church-platform-implementation.md](./2026-07-09--church-platform-implementation.md)  
**Issue:** [#012](../issues/2026-07-09--012--unify-services-remove-contact-persons.md)  
**Related:** [#008](../issues/2026-07-09--008--visibility-layer.md)

## Założenie

Jeden model danych: **osoba + służba** (`person` + `service_assignment`). Brak osobnej encji „osoba kontaktowa”. Widoczność na publicznej karcie zboru sterowana przełącznikami w formularzu edycji.

## Widoczność — trzy poziomy kontroli

```
service_assignment
├── show_on_church_card     → czy wpis (imię, funkcja, opis) jest na karcie
├── phone_visibility        → widoczność numeru (jeśli wypełniony)
└── email_visibility        → widoczność e-maila (jeśli wypełniony)
```

Wartości (zgodne z #008): `hidden` | `public` | `authenticated` | `pastors`.

**MVP uproszczenie:** boolean `is_public` per pole → migracja do enum w fazie #008.

### Domyślne wartości (propozycja)

| Pole | Domyślnie | Uzasadnienie |
|------|-----------|--------------|
| `show_on_church_card` | `public` | Pastor/diakon zwykle widoczny |
| `phone_visibility` | `public` jeśli phone ustawiony | Kontakt dla gości |
| `email_visibility` | `authenticated` | Mniej spamu; zalogowani widzą |

## UI — `ChurchPeopleSection`

Przy każdym przypisaniu (lista + formularz dodawania):

```
☑ Widoczne na karcie zboru
Telefon [+48 ...]   ☐ Widoczny publicznie
E-mail  [....]      ☐ Widoczny publicznie
```

Checkboxy mapowane na enum lub bool w API.

## API

Rozszerzenie `ServiceAssignment` / `Person` response:

- `showOnChurchCard` / `visibility`
- `phoneVisibility`
- `emailVisibility`

`VisibilityService` (#008) filtruje pola w publicznym `GET /churches/{id}/public`.

## Migracja z `congregation_contact_persons`

1. Dla każdego rekordu: utwórz `person` + `service_assignment`
2. Mapuj `title` → `service_type` (patrz `TITLE_TO_SERVICE_SLUG`) lub `custom_service_name`
3. Ustaw `show_on_church_card = public` (dotychczasowe contact persons były publiczne)
4. Usuń tabelę / endpoint po okresie przejściowym

## Usunięcie duplikatu UI

- Usunąć formularz „Osoby kontaktowe” z `EditCongregationPage.vue`
- Jedna sekcja: `ChurchPeopleSection`

## Zrealizowane (2026-07-09)

- [x] Migracja `057` — kolumny boolean na `service_assignments`
- [x] API create/update/list z polami widoczności
- [x] `ChurchPeopleSection` — przełączniki przy dodawaniu i na liście
- [x] Usunięcie sekcji contact persons z `EditCongregationPage`
- [x] Publiczna lista zborów — kontakt z `list_public_card_assignments`
- [x] Backfill migracji `contact_persons` → assignments

## Poza zakresem (następne kroki)

- Widoczność adresu fizycznego zboru (osobny workflow `address.status`)
- Listy mailingowe — [mailing-lists.md](./2026-07-09--mailing-lists.md)

## Related

- [church-people-and-services.md](./2026-07-09--church-people-and-services.md) — model osób i służb
- [#013](../issues/2026-07-09--013--service-type-select-not-visible.md) — bug selecta służb
