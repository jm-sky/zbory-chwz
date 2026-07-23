# OAuth GitHub — logowanie przez GitHub

**Status:** `done`  
**Created:** 2026-07-07  
**Moduł:** `auth` (shared core)  
**Source:** [gear-stack #014](../../gear-stack/docs/issues/2026-07-07--014--oauth-github-login.md) · [AI-workspace](../../AI-workspace)

## Problem

Brak logowania przez GitHub OAuth — tylko Google i Facebook.

## Zakres (backport)

- [x] Backend: `GitHubOAuthProvider`, `GITHUB_OAUTH_*`
- [x] Frontend: `OAuthGitHubButton`, trasa `/auth/github`, i18n (pl/en/ru)
- [x] `LoginForm.vue`, `RegisterForm.vue`

## Weryfikacja

Redirect URI produkcyjny: `https://zbory.chwz.waw.pl/auth/github`
