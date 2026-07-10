# Issue 037 — Backport JWT hardening i 2FA (shared core)

**Data:** 2026-07-08  
**Status:** `done` (2026-07-08)  
**Commits:** `3fbe4f3`, `f88d188`, `b9f008e`  
**Obszar:** shared core (auth, settings)

## Decyzja

Zsynchronizowanie z rodziną core (gear-stack): JWT hardening, poprawki 2FA, drobne poprawki frontend (`GuestLayout`, `PasswordInput`, `RadioGroup` vue-tsc).

## Implementacja

- `3fbe4f3` — `feat(core): backport JWT hardening, 2FA fixes, and shared-core sync`
- `f88d188` — `chore(core): GuestLayout, PasswordInput login, and npm in-range bumps`
- `b9f008e` — `fix(settings): cast RadioGroup value for vue-tsc compatibility`

## Weryfikacja

- Logowanie i 2FA bez regresji
- `vue-tsc` przechodzi na stronie settings
