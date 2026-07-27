# Zastane błędy: `NameError` w change-logu zboru i błędny tenant przy tworzeniu konta

**Status:** `todo`
**Created:** 2026-07-27
**Component:** `backend/app/modules/congregations/router.py`, `backend/app/modules/churches/repositories.py`, `backend/app/modules/churches/backfill.py`
**Related:** [#010](./2026-07-09--010--church-governance-actions.md) · [governance-ui-tasks plan](../plans/2026-07-27--governance-ui-tasks.md) (znalezione przy scopingu G0-G13, poza zakresem tego planu)

## Kontekst

Oba błędy zastane, wykryte przy scopingu planu governance UI dla #010. Nie są treścią #010 i nie
blokują G0-G13, ale dotyczą tego samego obszaru (change log / tworzenie kont przy przypisywaniu
służby), więc łatwo je pomylić z nowym UI audytu — stąd osobne issue.

## Bug 1 — `NameError` w `GET /congregations/{tenant_id}/change-log`

`congregations/router.py:610`:

```python
await _verify_change_log_access(tenant_id, current_user, access, acl_service)
```

`access` nie jest parametrem funkcji `get_change_log` (sygnatura `:601-609`: `tenant_id`,
`current_user`, `repo`, `tenant_repo`, `acl_service`, `skip`, `limit`) ani nazwą modułową.
Historia zmian adresu/kontaktu zboru jest zepsuta na każdym żądaniu (`NameError` w runtime, nie
tylko w edge case'ie).

- [ ] Ustalić, co `_verify_change_log_access` miało dostać jako `access` — prawdopodobnie wynik
  wywołania `acl_service` (np. `has_pastoral_access` / poziom widoczności), które zgubiono przy
  jakiejś wcześniejszej refaktoryzacji.
- [ ] Naprawić wywołanie, dodać test regresyjny na `GET /congregations/{tenant_id}/change-log`
  (dziś brak testu, który by to złapał — inaczej `NameError` nie przeszedłby review).

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
