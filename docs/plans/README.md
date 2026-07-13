# Plans

Plany implementacji funkcji i większych zmian.

## Status values

`todo` · `planned` · `in progress` · `done` · `verification needed`

## Index

| File | Summary | Status |
|------|---------|--------|
| [2026-07-09--church-platform.md](2026-07-09--church-platform.md) | Model zborów, uprawnienia i URL (koncepcja) | `planned` |
| [2026-07-09--organization-and-acl.md](2026-07-09--organization-and-acl.md) | Organizacja i ACL (koncepcja) | `planned` |
| [2026-07-09--church-platform-implementation.md](2026-07-09--church-platform-implementation.md) | **Implementacja** platformy zborów (fazy 0–5) | `planned` |
| [2026-07-09--church-assignment-visibility.md](2026-07-09--church-assignment-visibility.md) | Widoczność służb na karcie zboru (tel/e-mail) | `done` |
| [2026-07-09--people-groups.md](2026-07-09--people-groups.md) | Grupy ludzi — struktury organizacyjne | `in progress` |
| [2026-07-09--mailing-lists.md](2026-07-09--mailing-lists.md) | Eksport adresów e-mail (filtr + kopiowanie, bez wysyłki) + przeglądarka wszystkich osób (podgląd/edycja/scalanie duplikatów) | `done` |
| [2026-07-10--google-contacts-sync.md](2026-07-10--google-contacts-sync.md) | Synchronizacja z Google Contacts (import/export) | `planned` |
| [2026-07-11--congregation-address-text-import.md](2026-07-11--congregation-address-text-import.md) | Import adresów zborów z wklejonego tekstu (AI-assisted mapowanie + podgląd) | `verification needed` |
| [2026-07-13--clergy-email-updates.md](2026-07-13--clergy-email-updates.md) | Aktualizacje danych zboru przez e-mail od duchownych (IMAP + AI + auto-apply z weryfikacją zaufania) | `planned` |
| [2025-01-27--church-addresses.md](2025-01-27--church-addresses.md) | Adresy zborów — migracje, API, frontend | `planned` |
| [2025-01-27--backend-integration.md](2025-01-27--backend-integration.md) | Podstawowa integracja z backendem (auth, feature flag) | `done` |
| [2025-01-27--api-integration.md](2025-01-27--api-integration.md) | Integracja endpointów API z frontendem | `planned` |
| [2024-12-24--security-improvement.md](2024-12-24--security-improvement.md) | Plan bezpieczeństwa produkcyjnego (CSP, HSTS, WAF) | `in progress` |
| [2025-12-08--b2a-critical-fixes.md](2025-12-08--b2a-critical-fixes.md) | Krytyczne poprawki auth/WebAuthn (z analizy refaktoru) | `done` |
| [2025-12-23--phase-5-billing-completion.md](2025-12-23--phase-5-billing-completion.md) | Podsumowanie fazy 5 billing (legacy z core) | `done` |

### Plany funkcji (FEATURE-XXX)

| File | Feature | Status |
|------|---------|--------|
| [2025-01-21--feature-001-locale-detection.md](2025-01-21--feature-001-locale-detection.md) | Wykrywanie locale przeglądarki | `done` |
| [2025-01-21--feature-014-oauth-authentication.md](2025-01-21--feature-014-oauth-authentication.md) | OAuth | `done` |
| [2025-01-21--feature-015-recaptcha-integration.md](2025-01-21--feature-015-recaptcha-integration.md) | reCAPTCHA | `done` |
| [2025-01-22--feature-022-accessibility.md](2025-01-22--feature-022-accessibility.md) | Dostępność (a11y) | `planned` |
| [2026-03-01--feature-026-query-params-refactoring.md](2026-03-01--feature-026-query-params-refactoring.md) | Refaktoryzacja `returnTo` / `from` | `planned` |
| [2026-03-01--feature-028-back-button-navigation.md](2026-03-01--feature-028-back-button-navigation.md) | Nawigacja przycisku „Wróć” | `done` |
| [2026-03-01--feature-029-account-limits.md](2026-03-01--feature-029-account-limits.md) | Limity kont free/premium | `planned` |

When adding a new plan: create `YYYY-MM-DD--slug.md` and add a row here.

## Related

- [reviews/README.md](../reviews/README.md) — analizy i przeglądy przed planowaniem
- [issues/README.md](../issues/README.md) — follow-upy z planów i review
- [ROADMAP.md](../ROADMAP.md) — indeks funkcji i statusów
