# Issues

Błędy, usprawnienia i backporty ze wspólnego core — śledzone lokalnie.

## Status values

`todo` · `planned` · `in progress` · `done` · `verification needed`

## Index

| ID | File | Summary | Status |
|----|------|---------|--------|
| 001 | [2026-07-06--001--cli-users-list-wide.md](2026-07-06--001--cli-users-list-wide.md) | CLI `users list` — `--wide` jak ops-monitor | `todo` |
| 002 | [2026-07-06--002--cli-users-delete-soft-hard.md](2026-07-06--002--cli-users-delete-soft-hard.md) | CLI `users delete` — soft/hard jak family-recipes | `todo` |
| 003 | [2026-07-07--003--oauth-facebook-button-visibility.md](2026-07-07--003--oauth-facebook-button-visibility.md) | OAuth Facebook — `RegisterForm` (LoginForm już OK) | `done` |
| 004 | [2026-07-07--004--oauth-github-login.md](2026-07-07--004--oauth-github-login.md) | OAuth GitHub — logowanie przez GitHub | `done` |
| 005 | [2026-07-07--005--guest-layout-nav-z-index.md](2026-07-07--005--guest-layout-nav-z-index.md) | GuestLayout — pasek locale/dark mode pod logo (z-index) | `todo` |
| 006 | [2026-07-09--006--org-hierarchy-data-model.md](2026-07-09--006--org-hierarchy-data-model.md) | Hierarchia organizacyjna — model danych | `planned` |
| 007 | [2026-07-09--007--acl-roles-permissions.md](2026-07-09--007--acl-roles-permissions.md) | ACL — role i rozwiązywanie uprawnień | `planned` |
| 008 | [2026-07-09--008--visibility-layer.md](2026-07-09--008--visibility-layer.md) | Warstwa widoczności (public/authenticated/pastors) | `planned` |
| 009 | [2026-07-09--009--public-hierarchical-urls.md](2026-07-09--009--public-hierarchical-urls.md) | Publiczne URL `/kraj/miasto/slug` | `planned` |
| 010 | [2026-07-09--010--church-governance-actions.md](2026-07-09--010--church-governance-actions.md) | Governance — tworzenie zboru, przenoszenie, pastor | `planned` |
| 011 | [2026-07-09--011--postgres-full-text-search.md](2026-07-09--011--postgres-full-text-search.md) | Full-text search zborów (PostgreSQL tsvector) | `planned` |
| 012 | [2026-07-09--012--unify-services-remove-contact-persons.md](2026-07-09--012--unify-services-remove-contact-persons.md) | Tylko służby — widoczność osoby/tel/e-mail na karcie zboru | `verification needed` |
| 013 | [2026-07-09--013--service-type-select-not-visible.md](2026-07-09--013--service-type-select-not-visible.md) | Bug: niewidoczne pozycje selecta służb przy dodawaniu | `done` |
| 014 | [2026-07-09--014--people-groups.md](2026-07-09--014--people-groups.md) | Grupy ludzi (Prezydium, Grupa Ewangelizacji, …) | `planned` |
| 015 | [2026-07-09--015--mailing-lists.md](2026-07-09--015--mailing-lists.md) | Listy mailingowe (późniejsza faza) | `planned` |
| 016 | [2026-07-10--016--congregation-write-endpoint-for-non-admins.md](2026-07-10--016--congregation-write-endpoint-for-non-admins.md) | Pastor nie zapisze podstawowych danych zboru (endpoint admin-only) | `todo` |
| 017 | [2026-07-10--017--authorization-hardening-followups.md](2026-07-10--017--authorization-hardening-followups.md) | Hardening autoryzacji — `persons/search`, `POST /tenants`, `pastors` visibility | `todo` |
| 018 | [2026-07-10--018--congregation-address-data-quality.md](2026-07-10--018--congregation-address-data-quality.md) | Adresy — Świebodzin/Rzuchowa i Dankowice do weryfikacji | `todo` |
| 019 | [2026-07-09--019--church-phase-1-hierarchy.md](2026-07-09--019--church-phase-1-hierarchy.md) | Church platform Phase 1 — hierarchia, API, UI | `done` |
| 020 | [2026-07-09--020--edit-congregation-page-bugfixes.md](2026-07-09--020--edit-congregation-page-bugfixes.md) | Edycja zboru — błędy, nawigacja, status, widoczność | `done` |
| 021 | [2026-07-09--021--people-services-section-ux.md](2026-07-09--021--people-services-section-ux.md) | Ludzie i służby — UX widoczności, edycji, ról | `done` |
| 022 | [2026-07-09--022--congregation-list-search.md](2026-07-09--022--congregation-list-search.md) | Lista zborów — prosta wyszukiwarka | `done` |
| 023 | [2026-07-09--023--visibility-picker-icon-only.md](2026-07-09--023--visibility-picker-icon-only.md) | Picker widoczności e-mail/tel — ikona w stanie zwiniętym | `done` |
| 024 | [2026-07-09--024--multiple-card-contacts-show-on-card.md](2026-07-09--024--multiple-card-contacts-show-on-card.md) | Wiele kontaktów na karcie + „Pokaż na wizytówce” | `done` |
| 025 | [2026-07-10--025--congregation-export-json-markdown-filters.md](2026-07-10--025--congregation-export-json-markdown-filters.md) | Eksport JSON/Markdown + filtry listy | `done` |
| 026 | [2026-07-10--026--country-iso-province-normalization.md](2026-07-10--026--country-iso-province-normalization.md) | Kraj ISO alpha-2 + normalizacja województw | `done` |
| 027 | [2026-07-10--027--security-review-acl-hardening.md](2026-07-10--027--security-review-acl-hardening.md) | Review platformy — dokument w docs/reviews/ | `done` |
| 028 | [2026-07-10--028--congregation-create-from-list.md](2026-07-10--028--congregation-create-from-list.md) | Tworzenie zboru z listy publicznej | `done` |
| 029 | [2026-07-09--029--pwa-branding-zbory-chwz.md](2026-07-09--029--pwa-branding-zbory-chwz.md) | Rebranding PWA Gear Stack → Zbory CHWZ | `done` |
| 030 | [2026-07-10--030--acl-endpoint-enforcement.md](2026-07-10--030--acl-endpoint-enforcement.md) | Enforcement ACL na endpointach congregation/church | `done` |
| 031 | [2026-07-10--031--tenant-soft-delete-church-provisioning.md](2026-07-10--031--tenant-soft-delete-church-provisioning.md) | Soft delete tenantów + provisioning church | `done` |
| 032 | [2026-07-10--032--congregation-delete-from-list.md](2026-07-10--032--congregation-delete-from-list.md) | Usuwanie zboru z listy (soft delete) | `done` |
| 033 | [2026-07-10--033--tanstack-query-cache-invalidation.md](2026-07-10--033--tanstack-query-cache-invalidation.md) | TanStack Query — invalidacja po edycji | `done` |
| 034 | [2026-07-10--034--export-in-three-dot-menu.md](2026-07-10--034--export-in-three-dot-menu.md) | Eksport w menu ⋯ | `done` |
| 035 | [2026-07-09--035--visibility-enum-acl-tables.md](2026-07-09--035--visibility-enum-acl-tables.md) | Widoczność enum + tabele ACL (migracje 058–059) | `done` |
| 036 | [2026-07-09--036--card-visibility-rendering.md](2026-07-09--036--card-visibility-rendering.md) | Karta zboru — renderowanie widoczności kontaktu | `done` |
| 037 | [2026-07-08--037--backport-jwt-2fa-shared-core.md](2026-07-08--037--backport-jwt-2fa-shared-core.md) | Backport JWT hardening i 2FA (shared core) | `done` |

When adding a new issue: pick next `NNN`, create `YYYY-MM-DD--NNN--slug.md`, add a row here.
