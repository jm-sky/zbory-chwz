# Issue 039 — Backport: hardening rate limiting, admin auth, WebAuthn login

**Data:** 2026-07-20
**Status:** `done` (2026-07-20)
**Źródło:** [.docs/issues/2026-07-20--016--project-review-sweep.md](../../../.docs/issues/2026-07-20--016--project-review-sweep.md) (meta-repo) — review ops-monitor wykrył, że 5 z 6 findings to bugi w gear-stack (źródle prawdy rodziny), nie regresja ops-monitor. Naprawione najpierw w gear-stack, potem backportowane 1:1 do ops-monitor, teraz do zbory-chwz.

## Kontekst

Wszystkie poniższe znaleziska zweryfikowano jako identycznie obecne w zbory-chwz przed backportem (nie zakładano na podstawie samego wzorca — sprawdzono kod plik po pliku).

## Zmiany

1. **Authorization bypass (`/users/*` router)** — `update_user`/`delete_user`/`hard_delete_user` wołały repozytorium bezpośrednio, pomijając ochronę Ownera/protected-user, którą `AdminService` już egzekwował. Wydzielono współdzielony guard `enforce_user_mutation_permissions` (`app/modules/admin/authorization.py`), używany teraz przez oba miejsca.
2. **WebAuthn authentication — realna weryfikacja** — `complete_authentication` był zaślepką (`# TODO: Full WebAuthn verification`) bez sprawdzenia podpisu. Przepisano `initiate_authentication`/`complete_authentication` na użycie biblioteki `webauthn` (`generate_authentication_options` / `verify_authentication_response`) analogicznie do już poprawnej ścieżki rejestracji.
3. **Logowanie z 2FA było funkcjonalnie zepsute (fail-closed lockout)** — `verify_totp_login` mintował tokeny bez `tfaVerified: True`, więc włączenie 2FA blokowało konto zaraz po udanym sprawdzeniu kodu. Endpointy passkey-login (`/webauthn/authenticate/{initiate,complete}`) wymagały `CurrentUser`, którego nie da się spełnić tokenem `tfaPending` w trakcie logowania (chicken-and-egg) — przepisane na publiczne endpointy z `twoFactorToken` w body, analogicznie do `/totp/verify-login`. Frontend (`twoFactorService.ts`, `useWebAuthn.ts`) też był niedokończony — nie wysyłał `twoFactorToken` i nie zapisywał tokenów po sukcesie.
4. **Rate limiting nie działał** — `setup_limiter(app)` nigdy niewywoływany w `create_app()`; `get_client_ip` ufał lewemu (klienckiemu, spoofowalnemu) segmentowi `X-Forwarded-For` zamiast prawemu (dopisywanemu przez Caddy).
5. **Martwy kod** — usunięto zawsze-zepsuty `POST /api/users/` (bezwarunkowy `NotImplementedError`) oraz nieużywany, równoległy stos `app/exceptions/`.
6. **Zależności** — podbito `Pillow`/`jinja2`/`python-dotenv` powyżej znanych CVE.

## Weryfikacja

- Nowe testy: `tests/test_admin_authorization.py`, `tests/test_rate_limiter.py`, `tests/test_two_factor_login.py` (18 testów, wszystkie przechodzą)
- Pełny `pytest` — 381 passed, 2 pre-existing niepowiązane failures (`test_convert_empty_strings_middleware.py`, ten sam bug co w gear-stack/ops-monitor, niedotknięty tą zmianą)
- `black`, `mypy` — zero nowych błędów w zmienionych plikach (pre-existing błędy w nietkniętych plikach, np. `cli/commands/db.py`, `scripts/scrape_chwz_congregations.py`)
- `pnpm type-check`, `pnpm lint` — czysto

## Uwaga

Ten backport nie dotyka osobnego, wcześniejszego security/ACL review z 2026-07-10 ([#027](./2026-07-10--027--security-review-acl-hardening.md)) — to inny temat (autoryzacja domenowa `congregations`).
