# Issue 024 — Wiele kontaktów na karcie zboru + „Pokaż na wizytówce”

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commit:** `7bfa9a2`  
**Component:** `CongregationsList.vue`, `ChurchPeopleSection.vue`  
**Related:** [#012](./2026-07-09--012--unify-services-remove-contact-persons.md)

## Prompt (Cursor)

> Na karcie zboru widsc pierwsza osobe ze sluzb. Brakuje mozlieosci zmiany/wyboru osoby, gdy jest ich wiecej. Mozna dodsc sortowanie lub jakby checkbox "Pokaz na wizytowce"

*(sesja `6529d6e4`)*

## Decyzja

Zamiast implicit „pierwsza osoba z listy”:

- Flaga **`show_on_card`** na `service_assignment` — użytkownik wybiera, kto trafia na publiczną kartę
- **Wiele osób** może mieć flagę (np. pastor + diakon) — karta pokazuje wszystkich z `show_on_card=true`
- Osobne flagi widoczności telefonu/e-mailu (już w [#012](./2026-07-09--012--unify-services-remove-contact-persons.md))

## Implementacja

- Commit `7bfa9a2` — `feat(congregations): show multiple card contacts with show-on-card checkbox`
- Backend: pole `show_on_card` w API assignments

## Weryfikacja

- Dwie osoby w służbie, obie z checkboxem → obie na karcie listy
- Żadna z flagą → karta bez sekcji kontaktu (lub fallback do pierwszej publicznej — sprawdzić produkt)
