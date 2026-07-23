# Adresy zborów — dwa rekordy do ręcznej weryfikacji

**Status:** `todo`
**Created:** 2026-07-10
**Related:** migracja `backend/migrations/061_normalize_country_and_province.py`

## Problem

Dane zborów pochodzą ze scrape'a `chwz.info.pl/lista-zborow/`. Migracja 061
znormalizowała `country` do ISO 3166-1 alpha-2 i uzupełniła `city` oraz
`province` tam, gdzie dało się to zrobić jednoznacznie (31 z 33 adresów).

Dwa rekordy zostały **celowo nietknięte** — wymagają decyzji człowieka, bo
zgadywanie wpisałoby do bazy błędne dane.

## Do poprawienia

| Zbór | Co jest w bazie | Problem |
|------|-----------------|---------|
| `ZBÓR W ŚWIEBODZINIE` | `city = 'Rzuchowa'`, `postal_code = '33-114'` | Świebodzin leży w woj. lubuskim, a Rzuchowa (33-114) w małopolskim. Scrape sparował nazwę zboru z cudzym adresem. `province` zostało `NULL`. |
| `ZBÓR W DANKOWICACH` | `city = 'Dankowice'`, brak kodu pocztowego | W Polsce jest kilka wsi o nazwie Dankowice (m.in. woj. śląskie, opolskie, lubelskie). Bez kodu pocztowego nie da się wskazać właściwej. `province` zostało `NULL`. |

## Skutek

Oba zbory nie pojawią się przy filtrowaniu po województwie (`province IS NULL`),
ale są normalnie widoczne na liście i w eksporcie.

## Acceptance criteria

- [ ] `ZBÓR W ŚWIEBODZINIE` ma miasto Świebodzin, kod pocztowy i `province = 'lubuskie'`
- [ ] `ZBÓR W DANKOWICACH` ma potwierdzony kod pocztowy i właściwe `province`
- [ ] Ten sam poprawiony adres trafia do `backend/app/seeders/congregations.py`,
      żeby świeży `db seed` nie przywrócił błędu

## Notes

- Źródło prawdy: kontakt z pastorami zborów albo `chwz.info.pl`
- `province` przechowujemy jako slug ASCII (`lubuskie`, `dolnoslaskie`) — patrz
  `backend/app/modules/congregations/geo.py`
- Seeder nie wpisuje już `city = 'Unknown'`; brak miasta = błąd przy seedowaniu
