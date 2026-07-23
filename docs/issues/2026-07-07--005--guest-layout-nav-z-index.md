# GuestLayout — pasek locale/dark mode pod logo (z-index)

**Status:** `todo`  
**Created:** 2026-07-07  
**Moduł:** `layouts` (shared core)  
**Source:** [gear-stack #015](../../gear-stack/docs/issues/2026-07-07--015--guest-layout-nav-z-index.md)

## Problem

Na `/auth/login` (`GuestLayoutCentered`) pasek LocaleToggle + DarkModeToggle jest **pod** logo; `backdrop-blur-sm` nie działa.

## Zakres

- [ ] `src/layouts/GuestLayoutCentered.vue` — `z-10` na `<nav>` (jak w `GuestLayoutCenteredGlass.vue`)

**Poprawić w każdym repo z rodziny core** — ten sam plik, ten sam brakujący `z-index`.

## Weryfikacja

Login → pasek nad logo, blur na gradiencie tła.
