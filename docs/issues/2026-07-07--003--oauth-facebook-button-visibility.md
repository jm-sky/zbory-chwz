# OAuth Facebook — widoczność przycisku niezależnie od Google

**Status:** `done`  
**Created:** 2026-07-07  
**Moduł:** `auth` (shared core)  
**Source:** [gear-stack #013](../../gear-stack/docs/issues/2026-07-07--013--oauth-facebook-button-visibility.md)

## Problem

`LoginForm.vue` ma już poprawny wzorzec (osobne `v-if` per provider).  
`RegisterForm.vue` nadal używa `v-if="config.oauth.google.enabled"` i zawsze renderuje `OAuthFacebookButton` w tej sekcji.

## Oczekiwane zachowanie

Spójnie z `LoginForm.vue`:

```vue
<template v-if="config.oauth.google.enabled || config.oauth.facebook.enabled">
  ...
  <OAuthGoogleButton v-if="config.oauth.google.enabled" />
  <OAuthFacebookButton v-if="config.oauth.facebook.enabled" />
</template>
```

## Zakres

- [ ] `RegisterForm.vue` — dopasować do `LoginForm.vue`

## Weryfikacja

Tylko Google / tylko Facebook / oba / żaden na `/register`.
