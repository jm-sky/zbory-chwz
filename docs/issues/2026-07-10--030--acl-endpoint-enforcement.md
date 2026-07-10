# Issue 030 — Enforcement ACL na endpointach congregation/church

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `2428f9f`  
**Z tego samego promptu:** [#027](./2026-07-10--027--security-review-acl-hardening.md), [#031](./2026-07-10--031--tenant-soft-delete-church-provisioning.md)

## Prompt (Claude Code)

Część follow-upu po review — „popraw oczywiste rzeczy” (sesja `1e556b31`).

## Decyzja

Review wykazał endpointy zwracające/zapisujące dane zboru **bez** `verify_tenant_access` / `PermissionService`. Naprawa: spójna autoryzacja na routerach `congregations` i `churches` zanim rozbudujemy pełny ACL ([#007](./2026-07-09--007--acl-roles-permissions.md)).

## Implementacja

- `2428f9f` — `fix(security): enforce access control on congregation and church endpoints`

## Weryfikacja

- Użytkownik bez dostępu do tenant_id → 403
- Testy autoryzacji w `test_congregations_authz.py` zielone
