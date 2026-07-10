# Issue 036 — Karta zboru — renderowanie poziomów widoczności kontaktu

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commit:** `cd5ab3b`  
**Component:** `CongregationsList.vue`, `ContactFieldWithVisibility.vue`, `visibility.ts`  
**Z tego samego promptu:** [#020](./2026-07-09--020--edit-congregation-page-bugfixes.md), [#023](./2026-07-09--023--visibility-picker-icon-only.md)

## Prompt (Cursor)

Część sesji `fc3f778c` (widoczność email/phone jako dropdown) + poprawki po implementacji enum ([#035](./2026-07-09--035--visibility-enum-acl-tables.md)).

## Decyzja

- Helper `visibility.ts` — mapowanie enum → ikona/etykieta
- Lista zborów respektuje widoczność kontaktów na karcie publicznej
- Dopracowanie `ContactFieldWithVisibility` po przejściu na enum

## Implementacja

- `cd5ab3b` — `Fixes` (frontend congregations)

## Weryfikacja

- Kontakt „tylko pastorzy” nie pokazuje pełnego emaila gościowi
- Ikony widoczności spójne między edycją a listą
