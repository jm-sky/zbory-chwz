# Issue 031 — Soft delete tenantów + provisioning wierszy church

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `c423c5c`  
**Z tego samego promptu:** [#027](./2026-07-10--027--security-review-acl-hardening.md), [#030](./2026-07-10--030--acl-endpoint-enforcement.md)

## Prompt (Claude Code)

> Popraw jeszcze cos.  
> Poza tym upewnij sie ze w UI da sie dodac i usunac zbor (soft delete)  
> Upewnij sie ze mam admin/owner rights - jan.madeyski@gmail.com

*(follow-up sesji `1e556b31`)*

## Decyzja

- **Soft delete** na `tenants` (`deleted_at`) — usuwanie zboru z panelu admina bez kasowania wierszy
- **Provisioning** — każdy istniejący tenant dostaje wiersz `churches` (wcześniej brak → błędy serializacji API)
- **Owner** dla `jan.madeyski@gmail.com` — potwierdzenie `is_owner` w DB

UI tworzenia zboru z listy publicznej → osobne issue [#028](./2026-07-10--028--congregation-create-from-list.md).

## Implementacja

- `c423c5c` — `fix(churches): repair serialization, provision church rows, soft delete tenants`
- Migracja `060_tenant_soft_delete.py`
- `churches/provisioning.py`, testy `test_tenant_lifecycle.py`

## Weryfikacja

- Admin soft-delete tenant → znika z listy admina, dane w DB z `deleted_at`
- `GET /churches/{id}` nie wywala serializacji dla starego tenanta
