# Issue 040 — Backport: OAuth session machinery + CSRF state store

**Data:** 2026-07-22
**Status:** `done` (2026-07-22)
**Źródło:** gear-stack issues 036 + 037
- [gear-stack 036 — OAuth login bypasses session machinery](../../../gear-stack/docs/issues/2026-07-21--036--oauth-login-bypasses-session-machinery.md)
- [gear-stack 037 — OAuth callback state not verified](../../../gear-stack/docs/issues/2026-07-21--037--oauth-callback-state-not-verified.md)

## Problem

zbory-chwz still had the **full** vulnerability:

1. **`login_with_oauth` minted tokens via raw `create_access_token`/`create_refresh_token`** with only `{"sub": user.id}` — no `jti`, no `tv`, no session tracking in Redis, no 2FA challenge. Password login already went through `_issue_login_tokens`; OAuth did not.
2. **OAuth CSRF `state` was never verified server-side** — `/oauth/auth-url` generated a random state and returned it to the client; `/oauth/callback` never checked it against a server-side store.

## Fix (backport from gear-stack)

1. Extract `_resolve_oauth_user`; route `login_with_oauth` through `_issue_login_tokens` → `LoginResponse`.
2. `AuthServiceWith2FA`: add `_build_two_factor_challenge`, refactor `login_user`, override `login_with_oauth` to honor 2FA.
3. Add `OAuthStateStore` (Redis, single-use, provider-bound); `store_state` on auth-url, `consume_state` on callback.

## Zmiany

| Plik | Zmiana |
|------|--------|
| `backend/app/core/oauth_state_store.py` | nowy — Redis single-use CSRF state store |
| `backend/app/modules/auth/service.py` | `_resolve_oauth_user` + `login_with_oauth` → `_issue_login_tokens` |
| `backend/app/modules/two_factor/auth_integration.py` | `_build_two_factor_challenge` + `login_with_oauth` override |
| `backend/app/modules/auth/router.py` | `store_state` / `consume_state` na auth-url i callback |
| `backend/tests/test_oauth_state_store.py` | nowy |
| `backend/tests/test_oauth_2fa_login.py` | nowy |
| `backend/tests/test_auth_service.py` | `TestLoginWithOAuth` |

## Weryfikacja

```bash
docker exec zbory-chwz-app python -m pytest \
  tests/test_oauth_state_store.py \
  tests/test_oauth_2fa_login.py \
  tests/test_auth_service.py -v
```

30 passed.
