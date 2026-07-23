# Issue 032 — Usuwanie zboru z listy publicznej (soft delete)

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `8caaa6f`  
**Component:** `CongregationsList.vue`  
**Related:** [#031](./2026-07-10--031--tenant-soft-delete-church-provisioning.md)  
**Z tego samego promptu:** [#028](./2026-07-10--028--congregation-create-from-list.md), [#033](./2026-07-10--033--tanstack-query-cache-invalidation.md), [#034](./2026-07-10--034--export-in-three-dot-menu.md)

## Prompt (Claude Code)

> 1. I still cant remove church.

*(sesja `52a186bf`)*

## Decyzja

Usuwanie z **listy zborów** (nie tylko panel admina z [#031](./2026-07-10--031--tenant-soft-delete-church-provisioning.md)) — akcja w menu wiersza, potwierdzenie, soft delete przez API tenantów.

## Implementacja

- `8caaa6f` — delete action w `CongregationsList.vue` (admin/owner)

## Weryfikacja

- Usunięty zbór znika z listy bez F5
- Operacja idempotentna / obsługa błędu 403 dla nie-admina
