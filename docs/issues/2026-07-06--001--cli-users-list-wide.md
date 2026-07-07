# CLI `users list` — flaga `--wide` (jak ops-monitor)

**Status:** `todo`  
**Created:** 2026-07-06  
**Source:** [ops-monitor/backend/cli/commands/users.py](../../../ops-monitor/backend/cli/commands/users.py) (`users list`)  
**Backport:** [backport-progress.md](../../../backport-progress.md)

## Problem

Brak `--wide`, brak interaktywnych promptów dla `detailed` / `wide`. Obecny `users list` ma tylko `--detailed` jako zwykły boolean.

## Oczekiwane zachowanie

Jak ops-monitor — pełne ID i email (`--wide`), interaktywne potwierdzenia gdy brak `--json`.

## Zakres

- [ ] `backend/cli/commands/users.py` — backport komendy `list`
- [ ] Zachować lokalne różnice w `create` (`--role`, guess name from email)

## Weryfikacja

```bash
./exec.sh users list --wide --detailed
```
