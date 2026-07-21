# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Zbory CHWZ started on 2025-12-28 from a shared Vue/FastAPI boilerplate (formerly Gear Stack).
> Earlier Gear Stack release history is not part of this product changelog.
> Intermediate 0.x entries below retrospectively document work shipped before the first tagged release.

## [Unreleased]

### Added
- CLI `users change-password` command to set a user's password by email or ID (admin override; invalidates existing sessions via token version bump).

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## [1.0.0] - 2026-07-18

First stable production release of **Zbory CHWZ** — public congregation directory and management platform for CHWZ.

### Added
- Production-ready congregation platform: public list/detail, authenticated editing, admin tools
- Maps: Leaflet on congregation profiles and address editor; aggregate map with distance filter and geolocation
- Encrypted GPS coordinates with server-side geocoding (Polish street-type abbreviation stripping)
- Congregation and all-congregations share links (visibility tiers including pastors; Public removed as creatable level)
- Change history on congregation detail pages (manual/paste edits) and person change history
- Clergy e-mail import pipeline (IMAP, AI extraction/verification, admin review queue)
- Google Contacts import (connect, mapping, tolerant matching, diffs, church linking)
- AI-assisted address/contact import from pasted text
- People directory: e-mail export and person browser with edit/merge
- People groups module
- PII encryption for sensitive congregation/member data
- List/grid view toggle, phone formatting, service-time descriptions

### Changed
- Unified people/services model (service assignments) replacing separate contact-person flow
- Split list visibility from profile visibility for people; manual display order for assignments
- Congregation list UX: filters in URL, tighter spacing, mobile header improvements

### Fixed
- Localized forgot-password / resend-verification API messages
- Distance-filter i18n key path
- E-mail styling (primary color, escaped HTML in templates)
- Deploy/pnpm install prompt after GitHub Actions runs
- Various mobile layout and AI-import matching fixes

### Security
- Hardened access control on congregation and church endpoints
- Encrypted coordinates and sensitive PII fields (`PII_ENCRYPTION_KEY` in Docker)

---

## [0.9.0] - 2026-07-16

### Added
- Encrypted GPS coordinates and server-side geocoding for congregations
- Leaflet map on congregation profile and address editor
- Aggregate congregation map with distance filtering and geolocation
- Congregation change history on the detail page; person change history
- Pastors visibility tier for share links

### Changed
- Moved congregation profile map to the bottom of the page
- Removed Public as a creatable share-link visibility level

### Fixed
- Distance-filter i18n key path
- Localized forgot-password / resend-verification API messages
- E-mail styling: blue primary color and escaped `<strong>` tags
- Strip Polish street-type abbreviations before geocoding (2026-07-17)

---

## [0.8.0] - 2026-07-15

### Added
- All-congregations share links, surfaced in the Admin panel
- Pass `PII_ENCRYPTION_KEY` into Docker

### Changed
- Tightened congregation list row / list-mode spacing

### Security
- Hardened protection of sensitive congregation/member data

---

## [0.7.0] - 2026-07-14

### Added
- Congregation share links
- List/grid view toggle and phone formatting

### Changed
- Google Contacts import UX: tolerant matching, diffs, new-church linking, collapse panels

### Fixed
- Stale diff on manual church match and default-selected contacts

---

## [0.6.0] - 2026-07-13

### Added
- Clergy e-mail import: config, DB schema, sender authorization
- IMAP polling for clergy e-mail import
- Second AI verification pass and auto-apply gate
- Admin review queue and change-log endpoints
- Frontend for clergy e-mail import queue and change history
- Optional description field on service times + working PATCH endpoint and edit form

### Changed
- Improved Google Contacts import UX (search/filters/select-visible, configurable keywords, church detection)

### Fixed
- Migration version collision (066 claimed by two independent PRs)
- Literal `"null"`-like strings from AI extraction normalized to `None`
- pnpm install prompt during manual deploy after GHA runs

---

## [0.5.0] - 2026-07-11

### Added
- Congregation detail page (strona główna zboru)
- Manual display order for service assignments
- Split list visibility from profile visibility for people
- AI-assisted address/contact import from pasted text
- Google Contacts: readonly connection, admin UI, mapping screen and DB import
- People directory: e-mail address export tool; person browser with edit and duplicate merge
- Person search-as-you-type autocomplete
- People groups module (backend + frontend)
- GitHub Actions deploy from `develop` branch

### Changed
- Dropped ContactPerson in favor of service assignments
- Moved person browser out of export tabs into its own page
- Updated system service types list and migrated legacy assignments

### Fixed
- Congregation detail layout and contact visibility
- Mobile layouts (header, people section, address editor, admin actions)
- AI import matching, phone comparisons, and contact field labels
- Profile visibility in add-person form for editors

---

## [0.4.0] - 2026-07-10

### Added
- Congregation export to JSON/Markdown (country, province, branch filters)
- Create/delete congregation actions; export tucked into menu
- Search filters persisted in URL query params
- Homepage list UX improvements and draft visibility

### Changed
- Split vendor libraries into manual chunks for better builds
- Require explicit `createAccount` for pastor user accounts

### Fixed
- Serialization, church row provisioning, soft-delete tenants
- Stale list cache after mutations
- Homepage header actions and mobile add-button layout

### Security
- Enforced access control on congregation and church endpoints

---

## [0.3.0] - 2026-07-09

### Added
- Church hierarchy Phase 1: model, API, branches and people UI
- Unified people/services with card visibility (`show_on_card`, phone/email public toggles)
- Multiple card contacts with show-on-card checkbox
- Church platform implementation plans and issues

### Changed
- Replaced remaining Gear Stack branding with Zbory CHWZ (PWA, docs, UI)
- Reorganized docs index and cross-links

### Fixed
- Edit page errors and people section UX
- Icon-only visibility picker on email/phone fields

---

## [0.2.0] - 2026-07-07

### Added
- Shared-core catch-up from reference boilerplate
- JWT hardening, 2FA fixes, and shared-core sync
- GuestLayout, PasswordInput on login
- Architecture notes: permissions, URLs, visibility, organization/ACL

### Fixed
- RegisterForm OAuth visibility aligned with LoginForm
- RadioGroup value cast for vue-tsc compatibility
- Congregation edit page form context (2025-12-29)

### Changed
- npm in-range dependency bumps
- Docker Compose project naming configuration

---

## [0.1.0] - 2025-12-28

Initial Zbory CHWZ product release (forked from shared boilerplate).

### Added
- Project rebrand and cleanup: removed Gear Stack / gear / billing / AI markdown modules
- Full congregations module: addresses, service times, contact persons
- Public congregations list on landing page (published filter)
- Admin: publish/unpublish, address form, scraped congregations seeder
- Congregation statuses including `published_unverified` / `need_verification`
- Edit and unpublish actions with dropdown menu
- i18n for congregations (PL/EN); Russian language support scaffold
- Sentry DSN configuration and user context tracking
- PWA icons/manifest for Zbory CHWZ
- Deployment scripts and Caddyfile for zbory-chwz domains
- Church addresses plan and congregation seeder

### Changed
- Disabled public user registration on frontend
- Updated ports and contact information
- Owner/admin navigation and post-login redirects

### Fixed
- Owner role indicators and Admin Dashboard link visibility
- Null safety in EditCongregationPage
- Facebook OAuth button hidden when not configured
