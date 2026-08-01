# Zastane błędy: `NameError` w change-logu zboru i błędny tenant przy tworzeniu konta

**Status:** `in progress` (Bug 1 done 2026-08-01; Bug 2 still open)
**Created:** 2026-07-27
**Component:** `backend/app/modules/congregations/router.py`, `backend/app/modules/churches/repositories.py`, `backend/app/modules/churches/backfill.py`
**Related:** [#010](./2026-07-09--010--church-governance-actions.md) · [#042](./2026-08-01--042--congregation-list-stale-after-edit.md) · [governance-ui-tasks plan](../plans/2026-07-27--governance-ui-tasks.md) (znalezione przy scopingu G0-G13, poza zakresem tego planu)

## Kontekst

Oba błędy zastane, wykryte przy scopingu planu governance UI dla #010. Nie są treścią #010 i nie
blokują G0-G13, ale dotyczą tego samego obszaru (change log / tworzenie kont przy przypisywaniu
służby), więc łatwo je pomylić z nowym UI audytu — stąd osobne issue.

## Bug 1 — `NameError` w `GET /congregations/{tenant_id}/change-log` — `done` (2026-08-01)

`congregations/router.py` — `get_change_log` wołał `_verify_change_log_access(..., access, ...)`,
ale **nie wstrzykiwał** `access: TenantAccessChecker`. Każde żądanie → 500 → czerwony toast
„Nie udało się pobrać historii zmian” (to **nie** był pusty brak historii).

### Fix

- [x] Dodać `access: Annotated[TenantAccessChecker, Depends(get_tenant_access_checker)]` do `get_change_log`
- [x] Usunąć nieużywany `tenant_repo` z sygnatury
- [x] Zaktualizować seed testów ACL (`ensure_acl_roles` + override `PermissionCache(None)`)
- [x] `tests/integration/congregations/test_change_log.py` — 6/6 pass
- [x] UI: `ChangeHistorySection` / `PersonChangeHistorySection` — przy residualnym błędzie chować
  sekcję bez czerwonego toastu (historia to UI poboczne)

## Bug 2 — `_ensure_tenant_membership` dopina do złego tenanta

`repositories.py:316`:

```python
await self._ensure_tenant_membership(church.tenant_id, user_db.id)
```

Po migracji na model `Church`/`Region`/`Community` (`backfill.py`), `church.tenant_id` dla
**każdego** zboru wskazuje na jeden organizacyjny tenant CHWZ (`_get_or_create_org_tenant`,
`backfill.py:~58-74`), nie na tenant przypisany do tego konkretnego zboru. Efekt: gdy
`_maybe_create_user_and_acl` tworzy konto dla nowej osoby przy przypisaniu do służby
(`repositories.py:~290-316`), nowy `TenantMembershipDB` wiąże użytkownika z organizacyjnym
tenantem CHWZ zamiast z tenantem zboru, w którym faktycznie służy.

- [ ] Ustalić właściwe źródło tenant_id dla nowego membership — czy to w ogóle powinno być
  `TenantMembershipDB` (legacy model sprzed ACL), czy ACL (`PermissionService` / `user_role_assignments`)
  już wystarcza i ten insert jest martwym/szkodliwym kodem do usunięcia.
- [ ] Sprawdzić, czy coś faktycznie czyta `TenantMembershipDB` dla kont tworzonych tą ścieżką —
  jeśli tak, naprawić `tenant_id`; jeśli nie, rozważyć usunięcie wywołania zamiast łatania.
- [ ] Test: utworzenie konta przez przypisanie do służby zboru A nie tworzy membership do
  organizacyjnego tenanta CHWZ ani do zboru B.

## Poza zakresem

Nic z governance UI (G0-G13, [plan](../plans/2026-07-27--governance-ui-tasks.md)) nie zależy od
naprawy tych dwóch błędów — nie blokują. Wspomniane tam wyłącznie jako kontekst.
