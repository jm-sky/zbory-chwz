# Issue 042 — Lista zborów nie odświeża się po edycji (query key + PWA cache)

**Status:** `done` (2026-08-01)
**Created:** 2026-08-01
**Component:** `useCongregations.ts`, `congregationKeys.ts`, `pwa.config.ts`, `ChangeHistorySection.vue`
**Related:** [#033](./2026-07-10--033--tanstack-query-cache-invalidation.md) · [#041](./2026-07-27--041--change-log-and-tenant-membership-bugs.md)

## Problem

Po aktualizacji zboru (np. Poznań) zmiany nie widać na liście zborów mimo udanego zapisu.
Dodatkowo przy edycji/szczegółach często pojawiał się czerwony toast „Nie udało się pobrać historii zmian”
(to osobny bug — [#041](./2026-07-27--041--change-log-and-tenant-membership-bugs.md) Bug 1).

## Obserwacje

1. Po `PATCH .../address` frontend robił `GET /api/congregations/detailed` (invalidate w ścieżce adresu działało).
2. Po `PATCH .../service-assignments/...` w logach **brak** kolejnego `GET /detailed` — mimo
   `invalidateQueries({ queryKey: congregationKeys.all })` w `ChurchPeopleSection`.
3. `useCongregations` wkładał `ComputedRef` do query key bez unwrap (w przeciwieństwie do
   `useCongregationDetail`) — matchowanie invalidate w Vue Query było zawodne.
4. PWA (`pwa.config.ts`): reguła `NetworkOnly` dla PII miała zły pattern
   `congregations/[^/]+/detailed` (wymaga ID) — lista `/congregations/detailed` wpadała w
   generic `NetworkFirst` + `api-cache` (5 min).

## Fix

- [x] `congregationKeys.list` / `detail` — `toValue(...)` w fabryce kluczy
- [x] `useCongregations` — `queryKey: computed(() => congregationKeys.list(isAuthenticated.value))`
- [x] PWA — `NetworkOnly` obejmuje `congregations/detailed` oraz `congregations/[^/]+/detailed`
- [x] Historia zmian (UI): przy błędzie ładowania sekcja chowa się cicho (bez czerwonego toastu);
  root cause 500 naprawiony w #041 Bug 1

## Weryfikacja

- [ ] Frontend build + hard refresh / nowy SW (PWA pattern zmienia się dopiero po deployu SW)
- [ ] Edycja osoby / „Pokaż na liście zborów” → powrót na listę pokazuje świeże dane bez F5
- [ ] Edycja adresu → to samo
- [ ] Historia zmian na edycji zboru: 200 + sekcja (lub pusta), bez toastu
