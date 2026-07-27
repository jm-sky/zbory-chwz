# Governance UI — plan implementacji (zadania G0–G13)

**Status:** `done`
**Created:** 2026-07-27
**Architektura:** [2026-07-25--acl-architecture.md](./2026-07-25--acl-architecture.md) — **przeczytaj §2, §5, §6, §7 przed G0**
**Poprzednik:** [2026-07-25--acl-implementation-tasks.md](./2026-07-25--acl-implementation-tasks.md) (T1–T12, zamknięte)
**Issue:** [#010](../issues/2026-07-09--010--church-governance-actions.md) — Faza 5 planu platformy
**Faza:** [church-platform-implementation.md](./2026-07-09--church-platform-implementation.md) — Faza 5 „Management UI & governance"

Domknięcie #010: invite flow, ekran nadawania ról dla biskupów, picker wyjątków `user_permissions`
i audit log zmian wrażliwych na uprawnienia. Blokada „czekamy na #007" odpadła — silnik ACL
(T1–T12) wszedł w `a69366c`, `9f970d7`, `aafb77d`.

**Zasady wspólne:**

- Przed commitem Pythona: `python -m black .` i `python -m mypy .` w `backend/` (CLAUDE.md).
- Testy backendu: `docker exec zbory-chwz-app python -m pytest tests/ -v`.
- Front: `pnpm type-check` i `pnpm lint` muszą być czyste; klucze i18n dodawane **równocześnie**
  do `pl.ts` i `en.ts` — `src/modules/congregations/i18n/congregations.i18n.spec.ts` weryfikuje
  parzystość zestawów kluczy i rozwiązywalność każdego literału `t('congregations...')`.
- Migracje: wzorzec z `backend/migrations/078_user_permissions.py` — `upgrade()` / `downgrade()`,
  `CREATE TABLE IF NOT EXISTS`, idempotentne. Wolne numery: **081** wzwyż.
- Konwencje Vue: `<script setup lang="ts">`, jawne generyki `ref<T>` / `computed<T>`, brak
  średników, dedykowane union types zamiast literałów w miejscu użycia (CLAUDE.md).
- **Nie ruszamy [#009](../issues/2026-07-09--009--public-hierarchical-urls.md)** (publiczne URL-e).

---

## Stan wyjściowy (zweryfikowany w kodzie 2026-07-27)

### Co jest

| Element | Gdzie |
|---|---|
| `PermissionService.resolve / has_anywhere / allowed_church_ids / permissions_for_user` | `churches/permission_service.py` |
| Cache Redis, snapshot grantów, `acl:epoch` | `churches/permission_cache.py` |
| Reguły nadawania: podzbiór, bramka elevated, `required_permission_for_service_type` | `churches/acl_grant_rules.py` |
| Governance API: `POST /churches`, `PATCH /{id}/region`, `PATCH /{id}/visibility` | `churches/router.py:106,161,176` |
| `GET /churches/me/permissions` + `usePermissions().can()` | `churches/router.py:55`, `src/shared/composables/usePermissions.ts` |
| Tabela `user_permissions` (allow/deny) — **tylko odczyt** | migracja 078, `churches/acl_models.py:34` |
| Kasowanie ACL przy usunięciu służby (`source_assignment_id`) | `churches/repositories.py:594` |
| Sekcja „Ludzie i służby" z checkboxem „Utwórz konto" i selectem roli | `src/modules/congregations/components/ChurchPeopleSection.vue` |
| Wyszukiwarka istniejącej osoby (P-7) — **zrobiona** | `src/shared/composables/usePersonAutocomplete.ts` |

### Czego nie ma

| Element | Dowód |
|---|---|
| Jakakolwiek ścieżka **zapisu** do `user_permissions` | brak endpointu i brak komendy CLI; tabela wyłącznie czytana (`permission_service.py:179`) i kasowana kaskadowo (`repositories.py:594`) |
| CRUD nadań ról | granty powstają wyłącznie jako efekt uboczny `POST /churches/{id}/service-assignments` |
| Invite / ustawienie hasła | `grep -i invite` w `backend/app` i `src/` → 0 trafień |
| Audit log uprawnień | są `person_change_log`, `congregation_change_log`, `email_audit_log`, `logs` — żaden nie dotyka ACL |
| Stan konta w API | `ServiceAssignmentResponse` (`churches/schemas.py:112`) i `PersonResponse` (`:56`) zwracają tylko `userId` |

> **Uwaga do #010:** issue mówi „wyjątki dostępne przez CLI/admina". W kodzie **nie ma ani CLI, ani
> API** do `user_permissions` — jedyną drogą jest dziś ręczny `INSERT`. Zakres G9 to buduje od zera.

### Cztery błędy blokujące UI governance

1. **Cache nigdy nie unieważniany przy zmianie grantów.** `PermissionCache.invalidate_user`
   (`permission_cache.py:105`) ma **zero wywołań**; `bump_epoch` wołany tylko w `repositories.py:633`
   (`move_region`). Architektura §7 przewiduje inwalidację per user przy zmianie
   `user_role_assignments` / `user_permissions` / usunięciu przypisania — kod tego nie robi.
   Skutek: nadanie roli działa dopiero po ≤300 s, więc **każda akcja nowego UI wygląda na zepsutą**.
2. **Zasięg `branch` nieosiągalny.** `scope_chain("branch", id)` (`permission_service.py:127-131`)
   zwraca łańcuch zboru **bez** `("branch", id)`, więc grant `branch_responsible` nigdy nie spełni
   `resolve(..., ("branch", id))`.
3. **`can()` nie rozwija łańcucha zasięgów.** `usePermissions.ts` dopasowuje wyłącznie
   `scopeType === 'church' && scopeId === churchId`. Biskup ma granty na `community` / `region`,
   więc dostaje `false` dla każdego zboru — ekran ról byłby dla niego pusty.
4. **UI oferuje role, które API odrzuci.** `ChurchPeopleSection.vue:116-125` uznaje za uprawnionego
   do ról ponad-zborowych każdego z `services.manage` **w zasięgu zboru**; `assert_can_grant_role`
   (`acl_grant_rules.py:52-58`) wymaga `services.manage` na zasięgu **`community`**.

Poza zakresem tego planu, ale w tym samym obszarze UI: `congregations/router.py:610` woła
`_verify_change_log_access(tenant_id, current_user, access, acl_service)`, gdzie `access` nie jest
parametrem funkcji (sygnatura `:601-609`) ani nazwą modułową → `NameError` na każdym żądaniu
historii zmian. Oraz `_ensure_tenant_membership(church.tenant_id, …)` (`repositories.py:316`) dopina
członkostwo do **organizacyjnego tenanta CHWZ** (`backfill.py:74`), nie do zboru. Oba w
[#041](../issues/2026-07-27--041--change-log-and-tenant-membership-bugs.md).

---

## Kolejność i zależności

```
G0 ─┬─ G1 ─ G2 ─ G3                     (invite)
    ├─ G4 ─ G5 ─┬─ G6 ─ G7              (ekran ról)
    └─ G8 ──────┘                       (audit log — przed G5, żeby granty logowały się od początku)
                 └─ G9 ─ G10            (picker wyjątków)
                    G11 ─ G12 ─ G13     (audit UI, testy E2E, dokumentacja)
```

**G0 jest twardym warunkiem wszystkiego.** Bez inwalidacji cache'a (G0.1) każda akcja governance
wygląda na nieudaną przez pięć minut, a bez rozwinięcia łańcucha na froncie (G0.3) biskup nie
zobaczy żadnego zboru.

Fazy: **G0** odblokowanie · **G1–G3** invite · **G4–G7** ekran ról · **G8, G11** audit log ·
**G9–G10** wyjątki · **G12–G13** domknięcie.

---

## Faza 0 — odblokowanie

### G0.1 · Inwalidacja cache przy zmianie grantów

**Pliki:** `backend/app/modules/churches/repositories.py`, `permission_cache.py`,
`permission_service.py`

- Wpiąć `PermissionCache.invalidate_user(user_id)` we wszystkie ścieżki zapisu:
  utworzenie `UserRoleAssignmentDB` (`repositories.py:358-366`), usunięcie przypisania służby
  (`repositories.py:594-595`), a docelowo także zapisy z G5 i G9.
- Inwalidacja musi być wołana **po** commicie transakcji — inaczej równoległy request odbuduje
  snapshot ze starych danych. Jeśli repozytorium nie ma dostępu do granicy transakcji,
  wystawić metodę `invalidate_users(ids)` wołaną z warstwy routera.
- Wyjątki z Redisa dalej połykane i logowane (§7 — fallback do bazy, nigdy `403`).

**Done gdy:** test integracyjny — nadanie roli jest widoczne w `resolve` w kolejnym żądaniu przy
**działającym** Redisie (dziś test przechodzi tylko dlatego, że wszystkie testy używają
`PermissionCache(None)`); test, że usunięcie przypisania natychmiast odbiera dostęp.

---

### G0.2 · `scope_chain` dokłada zasięg `branch`

**Pliki:** `backend/app/modules/churches/permission_service.py`

- `scope_chain("branch", id)` ma zwracać `[("branch", id), *scope_chain("church", branch.church_id)]`.
- Sprawdzić, czy `allowed_church_ids` i `has_anywhere` nie zakładają, że w łańcuchu są wyłącznie
  zasięgi zborowe i wyżej.

**Done gdy:** test — użytkownik z rolą `branch_responsible` nadaną na `("branch", id)` przechodzi
`resolve(user, "branch.manage", ("branch", id))` i **nie** przechodzi go dla innej placówki
tego samego zboru.

---

### G0.3 · Efektywne uprawnienia per zbór w `/me/permissions`

**Pliki:** `backend/app/modules/churches/permission_service.py`, `schemas.py`,
`src/shared/composables/usePermissions.ts`

- `MePermissionsResponse` dostaje pole `churches: [{ churchId, permissions: [...] }]` obok
  istniejącego `scopes` (`scopes` zostaje — ekran z G6 operuje na zasięgach, nie na zborach).
- Liczone **jednym zapytaniem**: wczytać `churches(id, region_id, community_id)`, a następnie
  w pamięci przeciąć łańcuch każdego zboru ze snapshotem grantów. Dla `isAdmin` / `isOwner`
  zostaje dzisiejsza umowa „pusto = wszystko" — front i tak zwiera obwód na tych flagach.
- Przy okazji przepisać `allowed_church_ids` (`permission_service.py:66`) na ten sam jednoprzebiegowy
  algorytm — dziś iteruje wszystkie zbory i woła `resolve()` per zbór (N zapytań na żądanie,
  wołane m.in. z `people-directory` i `persons/search`).
- `can(permission, churchId)` czyta z `churches`; bez `churchId` — jak dziś, „gdziekolwiek".

**Done gdy:** biskup regionalny dostaje `can('church.edit', <zbór w swoim rejonie>) === true`
i `false` dla zboru spoza rejonu; liczba zapytań do bazy w `/me/permissions` nie rośnie z liczbą
zborów (test licznikiem zapytań lub jawną asercją na jedno `select` po `churches`).

---

### G0.4 · `GET /churches/grantable-roles`

**Pliki:** `backend/app/modules/churches/router.py`, `schemas.py`, `acl_grant_rules.py`,
`src/modules/congregations/components/ChurchPeopleSection.vue`,
`src/modules/congregations/types/visibility.types.ts`

- `GET /churches/grantable-roles?scopeType=&scopeId=` → `[{ name, scopeType, permissions[] }]`
  — role, które **wołający** może nadać w tym zasięgu. Implementacja przechodzi po `ROLE_SEED`
  i odpytuje tę samą funkcję, której używa zapis (`assert_can_grant_role` w wariancie
  zwracającym `bool` zamiast rzucającym `HTTPException`) — jedno źródło prawdy, żeby lista
  nie rozjechała się z egzekwowaniem.
- Front przestaje zgadywać: `canGrantElevatedRoles` i filtr po `ELEVATED_ACL_ROLES`
  (`ChurchPeopleSection.vue:116-125`) znikają, select roli zasila się odpowiedzią API.
  Stałe `CHURCH_ACL_ROLES` / `ELEVATED_ACL_ROLES` w `visibility.types.ts` przestają być listą
  do renderowania (typ `ChurchAclRole` może zostać, ale trzeba dołożyć `branch_responsible`,
  którego dziś w unii nie ma).

**Done gdy:** pastor (`services.manage` tylko w zborze) nie widzi `bishop` ani `regional_bishop`
na liście; test API porównuje listę z wynikiem `assert_can_grant_role` dla każdej roli z seeda
i każdego typu aktora z macierzy §11.

---

## Faza 1 — invite flow

### G1 · Model i token zaproszenia

**Pliki:** `backend/migrations/081_user_invitations.py` (nowy),
`backend/app/modules/auth/db_models.py`, `models.py`, `auth_utils.py`,
`backend/app/core/config.py`

- Migracja 081 dokłada do `users`: `invite_token` TEXT, `invite_token_expiry` TIMESTAMPTZ,
  `invited_at` TIMESTAMPTZ, `invited_by` VARCHAR(36) REFERENCES `users(id)` ON DELETE SET NULL.
- **Osobne kolumny, nie reuse `reset_token`.** Przy współdzieleniu jednej pary kolumn „zapomniałem
  hasła" wysłane przez zaproszonego kasuje jego zaproszenie i odwrotnie — cicha awaria, trudna
  do zdiagnozowania. Reuse dotyczy **infrastruktury** (kodowanie tokenu, `EmailService`, strona
  ustawiania hasła), nie magazynu.
- `create_invite_token(data)` w `auth_utils.py` obok `create_password_reset_token` (`:166`),
  `token_type="invite"`, TTL z nowego `settings.security.invite_token_expires_hours`
  (domyślnie **168 h** — zaproszenie idzie do pastora, godzina jak przy resecie to za mało).
- `User.set_invite_token` / `clear_invite_token` / `is_invite_token_valid` w konwencji
  `set_reset_token` (`auth/models.py:95-115`) — `secrets.compare_digest` + sprawdzenie `type`
  i `sub`, jak w istniejącym `is_reset_token_valid`.

**Done gdy:** `upgrade` i `downgrade` przechodzą dwukrotnie bez błędu; `mypy` czysty; test
jednostkowy — token typu `password_reset` **nie** przechodzi walidacji jako `invite` i odwrotnie.

---

### G2 · Endpoint zaproszenia, akceptacja i mail

**Pliki:** `backend/app/modules/churches/router.py`, `schemas.py`, `repositories.py`,
`backend/app/modules/auth/router.py`, `service.py`,
`backend/app/core/email/service.py`, `templates/invitation.html` (nowy),
`translations/{pl,en}.json`

- `POST /churches/{church_id}/service-assignments/{assignment_id}/invite` — zgodnie z decyzją
  z #010. Autoryzacja: `assert_can_assign_service_type` dla typu służby **tego** przypisania,
  czyli dokładnie to uprawnienie, które pozwoliło je utworzyć (§5.2). Nie `people.manage` na sztywno.
- Warunki wstępne: przypisanie należy do zboru z URL-a, osoba ma `email`, osoba ma konto
  (`person.user_id`). Brak konta → `409` z komunikatem „najpierw utwórz konto", nie ciche utworzenie.
- **Idempotentny „ponów zaproszenie":** kolejne wywołanie nadpisuje `invite_token`, co unieważnia
  poprzedni. Odpowiedź `{ invitedAt, invitationExpiresAt }` — **token nigdy nie trafia do odpowiedzi API**.
- `@rate_limit("10/hour")` w konwencji `search_persons` (`churches/router.py:85`) — bez tego endpoint
  jest narzędziem do zasypania cudzej skrzynki.
- `POST /auth/accept-invite { token, password }`: waliduje token, ustawia hasło
  (walidacja siły jak w `reset_password`), `is_active = true`, `is_email_verified = true`
  (zaproszenie dotarło pod ten adres — to dowód kontroli nad skrzynką), `token_version += 1`,
  czyści `invite_token`. **ACL nietknięte** — decyzja „Pastor ACL before `is_active`" z 2026-07-09.
- `EmailService.send_invitation_email` w konwencji `send_password_reset_email`
  (`core/email/service.py:278`), link `{frontend_url}/accept-invite?token=…`, szablon dziedziczy
  z `templates/base.html`, teksty w `translations/pl.json` i `en.json`.
- **Ujednolicenie stanu konta:** `_maybe_create_user_and_acl` (`repositories.py:307`) tworzy dziś
  konto z `is_active = not is_pastor`. Niepastorzy dostają konto „aktywne" z losowym hasłem, którego
  nikt nie zna — aktywność pozorna. Nowe konta powstają **zawsze nieaktywne**, aktywuje je dopiero
  akceptacja zaproszenia. **To zmiana zachowania** — patrz ryzyka.

**Done gdy:** testy integracyjne — invite → accept → logowanie działa; ponowny invite unieważnia
poprzedni token; token po TTL odrzucony (`400`); brak uprawnienia do typu służby → `403`;
przypisanie z innego zboru → `404`; odpowiedź nie zawiera tokenu; akceptacja nie zmienia żadnego
wiersza w `user_role_assignments` ani `user_permissions`.

---

### G3 · UI zaproszenia i stanu konta

**Pliki:** `backend/app/modules/churches/schemas.py`,
`src/modules/congregations/types/church.types.ts`,
`src/modules/congregations/components/ChurchPeopleSection.vue`,
`src/modules/congregations/services/churchApiService.ts`,
`src/modules/auth/pages/AcceptInvitePage.vue` (nowy), `src/modules/auth/routes.ts`,
`src/modules/congregations/i18n/locales/{pl,en}.ts`

- `ServiceAssignmentResponse` dostaje `account: AccountState | null`, gdzie
  `AccountState = { userId, status, invitedAt, invitationExpiresAt }`, a `status` to dedykowany
  union type `'none' | 'invited' | 'expired' | 'active'` (CLAUDE.md — union type zamiast literałów
  w interfejsie). Bez tego UI nie ma jak pokazać, kogo już zaproszono.
- W `ChurchPeopleSection.vue`: badge stanu konta w wierszu listy oraz akcja „Wyślij zaproszenie" /
  „Ponów zaproszenie", chowana przez `can(...)`. Po mutacji `queryClient.invalidateQueries`
  z `congregationKeys.all` — konwencja modułu (issue #033).
- `AcceptInvitePage.vue` na trasie `/accept-invite`, `meta.layout: 'guest'`, wzorowana na
  `ResetPasswordPage.vue`: token z query, formularz hasła z `vee-validate` + `zod`, obsługa
  wygasłego tokenu z podpowiedzią „poproś o ponowne zaproszenie".
- Klucze i18n w `pl.ts` **i** `en.ts` w tym samym commicie — inaczej `congregations.i18n.spec.ts`
  wywala build.

**Done gdy:** `pnpm type-check` i `pnpm lint` czyste; test vitest — akcja zaproszenia ukryta bez
uprawnienia i widoczna z uprawnieniem; badge pokazuje `expired` dla `invitationExpiresAt`
w przeszłości.

---

## Faza 2 — ekran nadawania ról

### G4 · Katalog ról w API

**Pliki:** `backend/app/modules/churches/router.py`, `schemas.py`

- `GET /churches/roles` → `[{ name, scopeType, permissions[] }]` z `ROLE_SEED` (`acl_seed.py:33`).
  UI ma pokazywać „co ta rola daje", a duplikowanie tabeli ról w TypeScripcie oznacza, że przy
  następnej zmianie seeda front będzie kłamać.

**Done gdy:** odpowiedź zgadza się z `ensure_acl_roles` co do zestawu ról i uprawnień; test
porównuje jedno z drugim, więc rozjazd seeda i API wywala testy.

---

### G5 · CRUD nadań ról

**Pliki:** `backend/app/modules/governance/` (nowy moduł: `router.py`, `schemas.py`,
`repositories.py`), `backend/app/api/router.py`, `backend/app/modules/churches/acl_grant_rules.py`

Dziś nie ma **żadnego** sposobu nadania roli inaczej niż przez utworzenie przypisania służby.

- `GET /governance/role-assignments?scopeType=&scopeId=` — nadania w danym zasięgu; wymaga
  `services.manage` w tym zasięgu. Zwraca `sourceAssignmentId`, żeby UI odróżniło nadania ręczne
  od pochodzących ze służby.
- `POST /governance/role-assignments { userId, roleName, scopeType, scopeId }` →
  `assert_can_grant_role` (bez zmian w regułach — §5.1). `source_assignment_id = NULL`.
- `DELETE /governance/role-assignments/{id}` → **nowa reguła, której architektura nie rozstrzyga:
  odebranie roli wymaga tych samych uprawnień co jej nadanie** (`assert_can_revoke_role`,
  ta sama ścieżka co `assert_can_grant_role`). Inaczej diakon mógłby zdjąć rolę biskupowi.
- Nadania z `source_assignment_id != NULL` **nie są** usuwalne tym endpointem → `409`
  z komunikatem „usuń przypisanie służby" (§5.3 mówi, że kasuje je usunięcie służby).
- **Blokada wykluczenia:** odmowa usunięcia ostatniego nadania `bishop` na zasięgu `community` →
  `409`. Bez tego da się doprowadzić do stanu, w którym ról ponad-zborowych nie nada już nikt
  poza adminem globalnym.
- Każdy zapis woła `invalidate_user` (G0.1) i `AclAuditService` (G8).

**Done gdy:** testy — biskup regionalny nadaje `pastor` w swoim rejonie (`201`) i nie nadaje
w cudzym (`403`); nikt poza admin/owner i posiadaczem `services.manage@community` nie nada
`bishop` (`403`); próba usunięcia nadania powiązanego ze służbą → `409`; próba usunięcia
ostatniego biskupa → `409`; po nadaniu uprawnienie działa natychmiast.

---

### G6 · Ekran „Zarządzanie rolami"

**Pliki:** `src/modules/governance/` (nowy moduł: `routes.ts`, `pages/GovernanceRolesPage.vue`,
`components/RoleAssignmentDialog.vue`, `services/governanceApiService.ts`, `types/`, `i18n/`),
`src/router/routes.ts`, `src/i18n/index.ts`

- **Nowy moduł, nie `/admin`.** Wszystkie trasy admina mają `requiresAdmin: true`
  (`src/modules/admin/routes.ts`), a biskup nie jest adminem globalnym — ekran pod `/admin`
  byłby dla niego niedostępny z definicji.
- Trasa `/governance/roles`, `meta: { layout: 'authenticated', requiresAuth: true,
  requiresPermission: 'services.manage', title: 'governance.roles.title' }`.
  Helpery ścieżek w konwencji `CongregationRoutePaths` (`congregations/routes.ts`) — obiekt
  `as const` z funkcjami dla tras parametryzowanych, bez wklejania stringów w komponentach.
- Układ: selektor zasięgu (wspólnota / rejon / zbór — z `scopes` z `/me/permissions`, przefiltrowane
  do tych, gdzie wołający ma `services.manage`) → `DataTable` nadań (osoba, rola, zasięg, źródło
  „ręczne / ze służby", data) → dialog nadania z wyszukiwarką osoby (`usePersonAutocomplete`)
  i selectem roli zasilanym z `GET /churches/grantable-roles` (G0.4).
- Wzorce do naśladowania: `DataTable.vue` ze slotami per kolumna i `meta: { pinned: 'right' }`
  dla akcji (jak `AdminUsersPage.vue`), dialogi shadcn-vue z `v-model:open`, `useHandleError`
  + `toast.success`, klucze TanStack Query w `utils/governanceKeys.ts` w konwencji
  `congregationKeys.ts`.
- Wejście na ekran: pozycja w `UserNav` / `AppHeader` widoczna przy `can('services.manage')`.

**Done gdy:** biskup regionalny widzi zbory swojego rejonu i nadaje w nich rolę; pastor nie widzi
pozycji w menu; `pnpm type-check` i `pnpm lint` czyste.

---

### G7 · Guard tras oparty o uprawnienie

**Pliki:** `src/shared/guards/permissionGuard.ts` (nowy), `src/router/index.ts`

- `permissionGuard` w konwencji `adminGuard.ts`: globalny `beforeEach`, czyta
  `to.matched.some(r => r.meta.requiresPermission)`, sprawdza `can(...)` z `usePermissions`
  (po poprawce G0.3), przekierowuje na `home` przy braku uprawnienia i na login przy braku sesji.
  Instalowany w `router/index.ts` po `protectAdminRoutes`.
- Typowanie `meta.requiresPermission` — rozszerzenie `RouteMeta` w deklaracji modułu
  `vue-router`, żeby literówka w nazwie uprawnienia wyszła w `type-check`.
- **Guard jest wyłącznie UX-owy** (§10) — autorytetem zostaje API.

**Done gdy:** test vitest z zamockowanym `usePermissions` — pastor przekierowany z `/governance/roles`,
biskup wpuszczony; niezalogowany trafia na login z `redirectTo`.

---

## Faza 3 — audit log

### G8 · Tabela i serwis audytu

**Pliki:** `backend/migrations/082_acl_audit_log.py` (nowy),
`backend/app/modules/governance/db_models.py`, `audit_service.py`

- Tabela `acl_audit_log` wzorowana na `person_change_log` (migracja 074, `directory/db_models.py:12`):
  `id`, `batch_id`, `actor_user_id` FK SET NULL, `actor_label` (`EncryptedString`),
  `target_user_id` FK SET NULL, `target_label` (`EncryptedString`), `action`, `scope_type`,
  `scope_id`, `role_name`, `permission`, `effect`, `old_value`, `new_value`, `source`, `created_at`.
  Indeksy: `(scope_type, scope_id, created_at DESC)` i `(target_user_id, created_at DESC)`.
- `actor_label` / `target_label` szyfrowane jak wartości w `person_change_log` — trzymamy nazwiska
  i adresy, a `persons` są szyfrowane w spoczynku (migracja 072); log nie może być obejściem.
- `AclAuditAction` jako `StrEnum`: `role.grant`, `role.revoke`, `permission.set`,
  `permission.clear`, `invite.sent`, `invite.accepted`, `assignment.create`, `assignment.delete`.
- `AclAuditService.record(...)` wołany z **każdej** ścieżki zapisu: G0.1 (kasowanie ze służby),
  G2 (invite), G5 (role), G9 (wyjątki), plus istniejące `_maybe_create_user_and_acl`.
  `batch_id` grupuje wiersze jednej akcji, jak w `person_change_log` (migracja 077).
- **Append-only** — brak endpointu i metody kasującej. `created_by` w `user_permissions` zostaje,
  ale audit log jest odtąd źródłem odpowiedzi na „kto to nadał".

**Done gdy:** `upgrade` / `downgrade` dwukrotnie bez błędu; test — nadanie roli, odebranie roli,
wysłanie zaproszenia i ustawienie wyjątku zostawiają po jednym wierszu z poprawnym aktorem,
celem i zasięgiem; usunięcie przypisania służby loguje `role.revoke` dla każdego skasowanego grantu.

---

### G11 · Odczyt i UI audytu

**Pliki:** `backend/app/modules/governance/router.py`,
`src/modules/governance/components/AclAuditSection.vue`

- `GET /governance/audit-log?scopeType=&scopeId=&targetUserId=&skip=&limit=` za `services.manage`
  w danym zasięgu; admin/owner widzi wszystko. Grupowanie po `batch_id` w konwencji
  `_group_person_change_log_by_batch` (`directory/router.py:55`).
- `AclAuditSection.vue` wzorowana na `ChangeHistorySection.vue`, osadzona na ekranie z G6.
  Renderuje „kto / komu / co / w jakim zasięgu / kiedy".

**Done gdy:** pastor nie odczyta logu spoza swojego zboru (`403`); paginacja i `total` działają;
brak jakiegokolwiek endpointu modyfikującego log.

---

## Faza 4 — picker wyjątków `user_permissions`

### G9 · CRUD wyjątków

**Pliki:** `backend/app/modules/governance/router.py`, `schemas.py`, `repositories.py`

- `GET /governance/user-permissions?userId=&scopeType=&scopeId=`,
  `PUT /governance/user-permissions { userId, scopeType, scopeId, permission, effect }` —
  **upsert**, bo `UNIQUE` jest na `(user_id, scope_type, scope_id, permission)` **bez** `effect`
  (§6), więc `allow` i `deny` nie mogą współistnieć,
  `DELETE /governance/user-permissions/{id}` — powrót do dziedziczenia z roli.
- Reguła autoryzacji — **zasada podzbioru §5.1 przeniesiona z ról na pojedyncze uprawnienia:**
  wołający musi mieć `services.manage` w tym zasięgu **oraz** sam posiadać uprawnienie, którym
  operuje. Admin/owner bez ograniczeń. Dotyczy tak samo `allow`, jak i `deny` — inaczej diakon
  odbierałby biskupowi `church.edit`.
- Zapis `created_by`, inwalidacja cache (G0.1), wpis do audytu (G8).
- Nie ruszamy wierszy z `source_assignment_id != NULL`.

**Done gdy:** testy — `deny` na zasięgu `community` blokuje pastora w zborze (potwierdza §2);
użytkownik bez `church.publish` nie ustawi `allow church.publish` (`403`); `PUT` dwa razy
z różnym `effect` daje jeden wiersz; `DELETE` przywraca uprawnienie z roli.

---

### G10 · Picker wyjątków w UI

**Pliki:** `src/modules/governance/components/UserPermissionsPanel.vue`,
`src/modules/governance/i18n/locales/{pl,en}.ts`

- Panel „Uprawnienia użytkownika" otwierany z wiersza tabeli z G6: lista uprawnień z katalogu
  (G4) × stan trójstanowy `dziedziczone` / `allow` / `deny`, plus kolumna „skąd" (nazwa roli
  i zasięg, z którego uprawnienie płynie). Dedykowany union type
  `PermissionEffectState = 'inherited' | 'allow' | 'deny'`.
- **Ostrzeżenie obowiązkowe:** `deny` wygrywa **w całym łańcuchu** (§2, „świadome uproszczenia"),
  więc `deny` ustawiony na `community` wyłącza uprawnienie we wszystkich zborach poniżej.
  Komunikat musi to mówić wprost przy wyborze zasięgu szerszego niż zbór.
- Uprawnienia, których wołający sam nie ma, renderowane jako wyłączone (serwer i tak odrzuci).

> **Odstępstwo od architektury §6.** Dokument z 2026-07-25 mówi: „Wyjątki `allow`/`deny` są
> dostępne wyłącznie dla admina (na start przez CLI)". Ten plan udostępnia je także posiadaczom
> `services.manage` w danym zasięgu, ograniczonym zasadą podzbioru z G9. Decyzja zakresowa
> z 2026-07-27; do naniesienia w §6 i changelogu `acl-architecture.md` (zadanie G13).

**Done gdy:** `pnpm type-check` i `pnpm lint` czyste; test vitest — przełącznik zablokowany dla
uprawnienia, którego wołający nie ma; ostrzeżenie o zasięgu widoczne dla `community` i `region`.

---

## Faza 5 — domknięcie

### G12 · Testy przekrojowe

**Pliki:** `backend/tests/integration/governance/`, `src/modules/governance/**/*.spec.ts`

- Rozszerzenie macierzy §11 o nowe akcje: nadanie roli, odebranie roli, wyjątek `allow`,
  wyjątek `deny`, zaproszenie, akceptacja zaproszenia — dla każdego typu aktora.
- Test „cache się nie rozjeżdża": nadanie roli → natychmiastowy dostęp → odebranie →
  natychmiastowa odmowa, przy **działającym** Redisie (dziś żaden test nie chodzi po tej ścieżce —
  wszystkie używają `PermissionCache(None)`).
- Test spójności UI/API: dla każdego aktora lista z `grantable-roles` równa się zbiorowi ról,
  dla których `POST /governance/role-assignments` kończy się sukcesem.

**Done gdy:** cała macierz zielona; `pnpm test:run` i `pytest tests/ -v` bez błędów.

---

### G13 · Aktualizacja dokumentacji

**Pliki:** `docs/issues/2026-07-09--010--church-governance-actions.md`,
`docs/issues/README.md`, `docs/plans/README.md`,
`docs/plans/2026-07-09--church-platform-implementation.md`,
`docs/plans/2026-07-25--acl-architecture.md`

- #010: status na `done`, odhaczone pozycje `## Scope`, sekcja „Stan" opisująca stan końcowy.
- `docs/issues/README.md` i `docs/plans/README.md`: statusy zaktualizowane, wiersz dla tego planu.
- `church-platform-implementation.md`: Faza 5 w tabeli „Status faz" → `done`, odhaczone punkty
  („Multi-community admin" zostaje odłożone — patrz niżej).
- `acl-architecture.md`: §6 uzupełniony o decyzję z G10 (wyjątki dla biskupów, nie tylko admina),
  wiersz w changelogu z datą.

**Done gdy:** statusy #010 zgodne w trzech miejscach (nagłówek issue, `issues/README.md`,
tabela „Status faz"); wszystkie linki względne rozwiązują się do istniejących plików.

---

## Reguły bezpieczeństwa

1. **API jest autorytetem, UI wyłącznie UX-em** (§10). `grantable-roles` i `can()` sterują
   widocznością; każdy zapis niezależnie przechodzi `assert_can_grant_role` / regułę podzbioru.
   Żadna reguła nie może istnieć tylko na froncie — dziś tak jest i produkuje błąd nr 4.
2. **Zasada podzbioru** (§5.1) obowiązuje też wyjątki: nie nadasz uprawnienia, którego sam nie masz
   w tym zasięgu — ani jako `allow`, ani jako `deny`.
3. **Odebranie wymaga tych samych uprawnień co nadanie.** Reguła nowa, spoza architektury.
4. **Role ponad-zborowe** (`bishop`, `regional_bishop`) widoczne w pickerze i nadawalne wyłącznie
   dla admin/owner albo posiadacza `services.manage` na zasięgu `community` (§5.1 pkt 3).
5. **Blokada wykluczenia się z systemu:** nie da się usunąć ostatniego nadania `bishop`
   na zasięgu `community`.
6. **Invite:** token jednorazowy, nadpisywany przy ponowieniu, `token_version += 1` przy akceptacji
   (unieważnia stare sesje), rate limit, token nigdy w odpowiedzi API, brak enumeracji użytkowników
   (jak w `request_password_reset`).
7. **`deny` jest globalny w łańcuchu** (§2) — UI musi ostrzegać przy zasięgu szerszym niż zbór.
8. **Audit log append-only**, dane osobowe aktora i celu szyfrowane `EncryptedString`.
9. **Nadania ze służby są nietykalne** dla governance API — kasuje je wyłącznie usunięcie
   przypisania (§5.3), inaczej ACL i lista służb rozjeżdżają się po cichu.

---

## Ryzyka

| Ryzyko | Skutek | Mitygacja |
|---|---|---|
| G0.1 pominięte lub zrobione przed commitem transakcji | każda akcja governance „nie działa" przez ≤5 min; użytkownicy klikają dwa razy i dublują nadania | G0 jako twardy warunek; inwalidacja po commicie; test na działającym Redisie (G12) |
| `allowed_church_ids` iteruje zbory z `resolve()` per zbór | nowe ekrany mnożą zapytania na każdym żądaniu | przepisane jednoprzebiegowo w G0.3 |
| Zmiana `is_active` na „zawsze nieaktywne do akceptacji" | istniejące konta z seeda i z dotychczasowego UI zmieniają stan | migracja obejmuje **tylko** konta bez ustawionego hasła (utworzone z losowym `token_urlsafe`); wypisać liczbę przed i po, jak w migracji 080 |
| Odstępstwo od architektury §6 (wyjątki dla biskupów) | rozjazd między kodem a dokumentem uznawanym za źródło prawdy | jawnie odnotowane w G10; aktualizacja §6 i changelogu w G13 |
| Spec parzystości i18n | build pada przy dodaniu klucza tylko do `pl.ts` | reguła „pl + en w tym samym commicie" w zasadach wspólnych |
| `deny` globalny w łańcuchu | biskup ustawia `deny` na wspólnocie i odcina uprawnienie wszystkim zborom, nie rozumiejąc dlaczego | ostrzeżenie w UI (G10) + test potwierdzający zachowanie (G9) |
| Nowy moduł `governance` na froncie i backendzie | rozrost struktury, ryzyko duplikacji z `churches` | granica: `churches` = dane zborów, `governance` = nadania, wyjątki, audyt; katalog ról i `grantable-roles` zostają w `churches`, bo dotyczą seeda ACL |
| `NameError` w `congregations/router.py:610` | historia zmian zboru jest zepsuta **już teraz**, tuż obok nowego UI audytu — łatwo pomylić przyczyny | [#041](../issues/2026-07-27--041--change-log-and-tenant-membership-bugs.md), nie mieszać z #010 |

---

## Czego ten plan nie obejmuje

| Element | Gdzie |
|---|---|
| Publiczne URL-e `/kraj/miasto/slug`, aliasy, 301 | [#009](../issues/2026-07-09--009--public-hierarchical-urls.md) |
| `NameError` w change-logu zboru, członkostwo dopinane do organizacyjnego tenanta CHWZ (`repositories.py:316`) | [#041](../issues/2026-07-27--041--change-log-and-tenant-membership-bugs.md) — poprawki zastane, nie treść #010 |
| Multi-community admin (punkt Fazy 5) | odłożone — jedna wspólnota CHWZ, brak przypadku użycia |
| `finances.manage`, `probation_ends_at`, nadpisywanie roli per przypisanie | architektura §4, §12 |
| Masowe nadania ról, powiadomienia mailowe o zmianie uprawnień | poza MVP |
| Wymuszenie `region_id` przy tworzeniu zboru przez biskupa regionalnego | zrobione w T9 |

---

## Changelog

| Data | Zmiana |
|---|---|
| 2026-07-27 | Dokument początkowy: invite flow, ekran nadawania ról, picker wyjątków `user_permissions`, audit log ACL; faza G0 z czterema błędami blokującymi wykrytymi w kodzie po T1–T12 |
