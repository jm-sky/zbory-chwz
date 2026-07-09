# Select służby — niewidoczne pozycje listy przy dodawaniu

**Status:** `done`  
**Created:** 2026-07-09  
**Component:** `ChurchPeopleSection.vue`, `EditCongregationPage.vue`  
**Related:** [#006](./2026-07-09--006--org-hierarchy-data-model.md)

## Problem

Przy dodawaniu osoby do służby w sekcji „Ludzie i służby” lista typów służb (Diakon, Pastor, …) **nie wyświetla pozycji** w rozwijanym `Select` — użytkownik widzi placeholder „Wybierz służbę”, ale opcje są niewidoczne lub lista jest pusta.

## Diagnostyka (2026-07-09)

- `SELECT count(*) FROM service_types` → **0** (tabela pusta — główna przyczyna pustej listy)
- `python -m cli db churches-backfill` — kończy się błędem `UniqueViolation` na `church_slug_aliases` (backfill nie dokańcza seeda typów służb)
- `jan.madeyski@gmail.com` — `is_owner = true` w DB (najwyższe uprawnienia)

## Rozwiązanie (2026-07-09)

- Naprawiono idempotentny `churches-backfill` (skip duplikatów slug aliasów)
- Zaseedowano 10 typów służb (`service_types`)
- `SelectContent` z `z-[100]` w `ChurchPeopleSection`

1. **Brak seeda** — tabela `service_types` pusta (backfill nie uruchomiony)
2. **Filtr scope** — frontend filtruje `scopeType === 'church'`; seed zawiera też typy `community` / `region` (to OK, ale church typy muszą istnieć)
3. **CSS / stacking** — `SelectContent` (`z-50`) przycinany przez `overflow: hidden` na rodzicu w `EditCongregationPage` lub konflikt z-index z layoutem
4. **Portal** — dropdown renderowany poza viewportem na mobile

## Scope

- [ ] Zweryfikować `GET /churches/service-types` — czy zwraca typy `church`
- [ ] Naprawić `churches-backfill` — idempotentny insert aliasów + seed `service_types` nawet gdy aliasy już istnieją
- [ ] Naprawić stacking (np. wyższy z-index, `overflow-visible` na sekcji, lub `SelectContent` w portalu z poprawnym kontenerem)
- [ ] Test manualny: otwarcie selecta pokazuje ≥6 pozycji (pastor, diakon, …)
- [ ] Test E2E lub komponentowy dla `ChurchPeopleSection`

## Acceptance criteria

- Po kliknięciu „Służba” widać pełną listę predefiniowanych typów służb
- Wybór pozycji ustawia wartość i wyświetla nazwę w triggerze
- Działa na desktop i mobile w kontekście strony edycji zboru

## Suggestions

- Dodać komunikat „Brak typów służb — uruchom migrację/backfill” gdy `serviceTypes.length === 0`
- Rozważyć `SelectContent` z `class="z-[100]"` w formularzach zagnieżdżonych w kartach z `overflow-hidden`
