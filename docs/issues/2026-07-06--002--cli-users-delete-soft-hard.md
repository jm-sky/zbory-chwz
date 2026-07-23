# CLI `users delete` — soft/hard delete (jak family-recipes)

**Status:** `todo`  
**Created:** 2026-07-06  
**Source:** [family-recipes/backend/cli/commands/users.py](../../../family-recipes/backend/cli/commands/users.py) (`users delete`)  
**Backport:** [backport-progress.md](../../../backport-progress.md)

## Problem

- CLI robi hard delete (raw `db.delete` lub zawsze `soft_delete=False`)
- brak flagi `--hard` i domyślnego soft delete
- repozytorium `delete_user` w zbory-chwz jest węższe niż w gear-stack (brak OAuth/2FA cleanup) — warto zsynchronizować przy okazji

## Oczekiwane zachowanie

Jak family-recipes:

- domyślnie soft delete przez `UserRepository.delete_user(soft_delete=True)`
- `--hard` — trwałe usunięcie
- komunikaty soft vs hard

## Zakres

- [ ] `backend/cli/commands/users.py` — `--hard`, repository zamiast raw delete
- [ ] (opcjonalnie) backport pełnego GDPR `delete_user` z gear-stack do repozytorium

## Weryfikacja

```bash
./exec.sh users delete user@example.com
./exec.sh users delete user@example.com --hard --yes
```
