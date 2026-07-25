# Pastor nie może zapisać podstawowych danych swojego zboru

**Status:** `done` (2026-07-25)
**Created:** 2026-07-10
**Commit:** `8b2f32f`
**Component:** `congregationApiService.ts`, `EditCongregationPage.vue`, `CongregationsList.vue`, `tenants/router.py`
**Related:** [#007](./2026-07-09--007--acl-roles-permissions.md) · [review 2026-07-10](../reviews/2026-07-10--church-platform-review.md) (BUG-2, BUG-3)

## Problem

Sekcja „Podstawowe informacje” (nazwa, opis, status) oraz akcja „Cofnij publikację” wołają `PATCH /admin/tenants/{id}`, który ma dependency `AdminOrOwnerUser`. Dla pastora i diakona to 403.

```typescript
// congregationApiService.ts
async updateCongregation(id: string, data: IUpdateCongregationRequest): Promise<void> {
  await apiClient.patch(`/admin/tenants/${id}`, data)   // admin-only
}
```

Dodatkowo `canManageCongregation()` w `CongregationsList.vue` sprawdza `congregation.role`, którego `PublicCongregationResponse` w ogóle nie zwraca — dropdown „Edytuj / Cofnij publikację” widzi wyłącznie admin. Pastor nie ma z UI żadnej ścieżki do edycji swojego zboru; strona `/congregations/:id/edit` jest osiągalna tylko przez wpisanie URL.

## Scope

- [x] `PATCH /congregations/{tenant_id}` — nazwa, opis, status; autoryzacja przez `verify_tenant_access` (docelowo `church.edit` z `PermissionService`)
- [x] `congregationApiService.updateCongregation()` → nowy endpoint; `/admin/tenants` zostaje dla panelu admina
- [x] Zwrócić `role` w odpowiedzi listy zborów dla zalogowanego użytkownika
- [x] `canManageCongregation()` oparte o realne pole
- [x] Test integracyjny: pastor zapisuje nazwę własnego zboru (200), cudzego (403)

## Acceptance criteria

- [x] Pastor widzi „Edytuj” przy swoim zborze i zapisuje wszystkie sekcje strony edycji
- [x] Pastor nie widzi i nie może edytować cudzego zboru
- [x] Admin zachowuje dotychczasowe możliwości

## Zamknięcie (2026-07-25)

Commit `8b2f32f` — tenant-scoped `PATCH /congregations/{id}`, `role` w `GET /congregations/detailed`,
testy w `tests/integration/congregations/test_congregations_authz.py`.

**Przeniesione do [#007](./2026-07-09--007--acl-roles-permissions.md):**

- autoryzacja przechodzi z `verify_tenant_access` (członkostwo) na `church.edit`
  z `PermissionService` — zadanie T7 w
  [acl-implementation-tasks.md](../plans/2026-07-25--acl-implementation-tasks.md);
- ograniczenie zmiany `status` dla nie-admina: rozstrzygnięte jako **uprawnienie `church.publish`**,
  nadane też pastorowi (patrz [#008](./2026-07-09--008--visibility-layer.md), decyzje 2026-07-25) —
  publikacja przechodzi na `churches.visibility`, nie `tenant.status`.
