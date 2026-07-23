# Issue 023 — Picker widoczności e-mail/telefon — tylko ikona w stanie zwiniętym

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commit:** `168a303`  
**Component:** `ContactFieldWithVisibility.vue`, `VisibilityLevelSelect.vue`

## Prompt (Cursor)

> Inputs for email and phone on edit page - visibility picker thats on the right side of input should show only icon when collapsed (default state).  
> *(sesja `39d248df`)*

> Trzeba poprawic input email i phone z pickerem widocznosci. Musi tam byc ikona bo tekst sie nie miesci. Tekst tylko po rozwinieciu dropdown.  
> *(sesja `79ba874d`)*

## Decyzja

W wąskim input group **tekst poziomu widoczności nie mieści się** obok pola e-mail/telefon. Domyślnie trigger pokazuje **tylko ikonę** (globe/lock/eye); pełna etykieta po rozwinięciu dropdown + tooltip.

## Implementacja

- Commit `168a303` — `fix(congregations): show icon-only visibility picker on email/phone fields`

## Weryfikacja

- Zwinięty stan: ikona + wyrównany border z inputem
- Rozwinięty: pełne nazwy poziomów widoczności
- Tooltip opisuje aktualny poziom
