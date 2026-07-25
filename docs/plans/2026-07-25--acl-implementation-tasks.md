# ACL — plan implementacji (zadania T1–T12)

**Status:** `planned`
**Created:** 2026-07-25
**Architektura:** [2026-07-25--acl-architecture.md](./2026-07-25--acl-architecture.md) — **przeczytaj przed T1**
**Issues:** [#007](../issues/2026-07-09--007--acl-roles-permissions.md) (T1–T9) · [#008](../issues/2026-07-09--008--visibility-layer.md) (T10–T12)

Rozbicie na zadania wykonywalne pojedynczo. Każde ma zamknięte kryterium akceptacji i nie wymaga
decyzji produktowych — te są rozstrzygnięte w dokumencie architektury.

**Zasady wspólne:**

- Przed commitem Pythona: `python -m black .` i `python -m mypy .` w `backend/` (CLAUDE.md).
- Testy: `docker exec zbory-chwz-app python -m pytest tests/ -v`.
- Migracje: wzorzec z `backend/migrations/059_acl_tables.py` — `upgrade()` / `downgrade()`,
  `CREATE TABLE IF NOT EXISTS`, idempotentne.
- Nie ruszamy `#009` (publiczne URL-e) ani `#010` (UI governance, invite, audit log).

## Kolejność i zależności

```
T1 ─ T2 ─ T3 ─ T4 ─ T5 ─┬─ T6 ─ T7 ─┬─ T8
                        │           └─ T9
                        └─────────────── T10 ─ T11 ─ T12
```

Fundament: T1–T5. Enforcement: T6–T9. Widoczność: T10–T12.
T10 nie zależy od T6/T7 — można je puścić równolegle, jeśli wygodniej.

---

## Faza A — fundament

### T1 · Tabela `user_permissions`

**Pliki:** `backend/migrations/078_user_permissions.py` (nowy), `backend/app/modules/churches/acl_models.py`

- Migracja wg schematu z architektury §6 (`UNIQUE (user_id, scope_type, scope_id, permission)` —
  **bez** `effect`), indeksy na `user_id` i `source_assignment_id`.
- Model `UserPermissionDB` obok istniejących w `acl_models.py`, w tej samej konwencji
  (`String(36)` PK, `generate_id()`, `DateTime(timezone=True)`).

**Done gdy:** `upgrade` i `downgrade` przechodzą dwukrotnie bez błędu; `mypy` czysty.

---

### T2 · Katalog uprawnień + naprawa seeda ról

**Pliki:** `backend/app/modules/churches/acl_seed.py`

- Stała `PERMISSIONS` (albo `StrEnum`) z pełnym katalogiem z architektury §4, łącznie
  z zarezerwowanymi `events.manage` / `documents.manage` i **bez** `finances.manage`.
- `ROLE_SEED` rozszerzony wg tabeli domyślnych ról (§4): dochodzą `church.view_pastoral`,
  `church.publish`, `church.delete`, `branch.manage` oraz rola `branch_responsible`.
  `diacon` **nie dostaje** `services.manage`.
- **Bug do naprawy:** `ensure_acl_roles` (`acl_seed.py:61`) dokłada `role_permissions` tylko przy
  tworzeniu nowej roli — na istniejącej bazie nowe uprawnienia nigdy nie wejdą. Ma robić upsert:
  dodać brakujące, usunąć te spoza seeda dla ról systemowych.
- `PASTORAL_ROLE_NAMES` / `ELEVATED_ROLE_NAMES` zostają na czas migracji, ale nowy kod ich nie
  używa — docelowo znikają razem z `AclService` (T7).

**Done gdy:** test, że `ensure_acl_roles` uruchomiony na bazie ze „starymi" rolami dokłada nowe
uprawnienia; role mają dokładnie zestawy z tabeli §4.

---

### T3 · `PermissionService`

**Pliki:** `backend/app/modules/churches/permission_service.py` (nowy),
`backend/app/modules/directory/repositories.py`

- Łańcuch zasięgów `branch → church → region → community` z pominięciem `NULL` `region_id`
  (architektura §2). Jedna funkcja `scope_chain(scope_type, scope_id) -> list[tuple[str, str]]`.
- `resolve(user, permission, scope) -> bool` wg algorytmu §2 — override admin/owner, `deny`
  wygrywa w całym łańcuchu.
- `has_anywhere(user, permission) -> bool`.
- `allowed_church_ids(user, permission) -> set[str] | None` — `None` = bez ograniczeń.
- **Reuse:** logika rozwijania zasięgów jest już w `DirectoryRepository.get_allowed_church_ids`
  (`directory/repositories.py:41`); przenieść ją do serwisu, dołożyć filtr po uprawnieniu,
  a `DirectoryRepository` ma wołać `PermissionService` zamiast trzymać kopię.
- Bez cache'a — cache dokłada T4 za tym samym interfejsem.

**Done gdy:** `tests/unit/churches/test_permission_service.py` pokrywa łańcuch zasięgów, `deny`
bijące rolę, `region_id = NULL`, override admina — **bez warstwy HTTP**.

---

### T4 · Cache Redis

**Pliki:** `backend/app/modules/churches/permission_cache.py` (nowy), `permission_service.py`

- Klucz `acl:v{epoch}:{user_id}` → snapshot grantów użytkownika (role rozwinięte do uprawnień
  + wyjątki). **Nie** cache'ować odpowiedzi per `(permission, scope)`. TTL 300 s.
- Inwalidacja per user przy zmianie `user_role_assignments` / `user_permissions` / usunięciu
  `service_assignment`.
- Globalny `acl:epoch` bumpowany przy zmianie `role_permissions`, seedzie ról oraz zmianie
  `churches.region_id` / `community_id`.
- **Redis niedostępny → zapytanie do bazy.** Wyjątki z Redisa logowane i połykane, nigdy nie
  zamieniane na `403`.

**Done gdy:** test z podmienionym klientem Redisa rzucającym wyjątkiem daje takie same wyniki jak
z działającym cache'em; test inwalidacji po nadaniu roli.

---

### T5 · `RequirePermission` + resolver `tenant_id → church_id`

**Pliki:** `backend/app/modules/churches/dependencies.py` (nowy)

- `get_permission_service()` w konwencji `get_acl_service` (`acl_service.py:68`).
- `RequirePermission(permission, *, param="church_id", scope_type="church")` — fabryka zależności
  FastAPI czytająca parametr ścieżki.
- Wariant `tenant_id`: mapowanie 1:1 (`churches.id == tenants.id`, `provisioning.py:66`,
  `backfill.py:71`), **odrzucający organizacyjny tenant CHWZ** (`seed_data.CHWZ_ORG_TENANT_NAME`),
  który nie ma wiersza w `churches`.
- `404` gdy zbór nie istnieje, `403` gdy istnieje a brak uprawnień.

**Done gdy:** test dependency na atrapie routera: 404 dla nieistniejącego, 403 dla bez uprawnień,
403 dla organizacyjnego tenanta CHWZ.

---

## Faza B — enforcement

### T6 · Migracja `tenant_memberships` → ACL + CLI

**Pliki:** `backend/migrations/079_membership_to_acl.py` (nowy),
`backend/cli/commands/acl.py` (nowy), `backend/cli/__init__.py`

- Migracja wg architektury §9: `owner` / `admin` → rola `pastor` w zasięgu `church`;
  `member` → `pastor` **tylko** przy pasterskim `service_assignment` w tym zborze
  (`seed_data.PASTOR_SERVICE_SLUGS`). Nadania migracyjne z `source_assignment_id = NULL`.
  Idempotentna.
- CLI `python -m cli acl migrate-memberships [--dry-run]` — nowe `typer.Typer()` zarejestrowane
  w `cli/__init__.py` obok `db_app` / `tenants_app` (linie 22–26). Dry-run wypisuje: kto dostanie
  rolę, kto straci dostęp mimo członkostwa, ile zborów bez rejonu.
- Migracja **nie** przełącza enforcement — to T7.

**Done gdy:** dwukrotne uruchomienie nie tworzy duplikatów; dry-run nic nie zapisuje; raport
zgadza się z tym, co robi tryb właściwy.

---

### T7 · Przełączenie autoryzacji na ACL + shadow log

**Pliki:** `backend/app/modules/tenants/access.py`, `backend/app/modules/churches/router.py`,
`backend/app/modules/congregations/router.py`, `backend/app/modules/tenants/router.py`,
`backend/app/modules/churches/acl_service.py`

- `verify_tenant_access` i `_verify_church_access` (`churches/router.py:34`) liczą uprawnienie
  przez `PermissionService` zamiast sprawdzać członkostwo.
- Wszystkie zapisy zborowe za `RequirePermission`: placówki → `branch.manage`, przypisania służb →
  wg T8, adres / godziny / profil → `church.edit`, usunięcie zboru → `church.delete`.
- **Shadow log:** żądanie odrzucone przez ACL, które przeszłoby po staremu (membership), loguje
  `acl.shadow_deny` z `user_id`, `church_id`, `permission`. Nie zmienia decyzji.
- `AclService.has_pastoral_access` (`acl_service.py:39`) zastąpiony przez
  `resolve(user, "church.view_pastoral", church)`; wywołania w `tenants/router.py` i
  `congregations/router.py:65` przepięte. `AclService` znika, gdy nie zostaną wywołania.

**Done gdy:** `tests/integration/congregations/test_congregations_authz.py`,
`tests/integration/churches/test_persons_search_authz.py`,
`tests/integration/tenants/test_tenant_creation_authz.py` zielone; nowy
`tests/integration/churches/test_permission_matrix.py` pokrywa macierz z architektury §11.

---

### T8 · Reguły nadawania ról i przypisywania służb

**Pliki:** `backend/app/modules/churches/repositories.py`, `backend/app/modules/churches/schemas.py`

- `_resolve_grant_role` (`repositories.py:356`) przechodzi z `can_grant_elevated_roles: bool` na
  trzy niezmienniki z architektury §5.1: podzbiór uprawnień nadającego, `services.manage`
  w zasięgu nadania, twarda bramka na `bishop` / `regional_bishop`.
- `required_permission_for_service_type(service_type)` wg §5.2 — sprawdzana przy `POST`, `PATCH`
  i `DELETE` przypisania; przy `PATCH` walidowane są **oba** typy (stary i nowy), żeby podniesienie
  „członek rady" → „pastor" nie omijało reguły.
- Usunięcie przypisania kasuje `user_role_assignments` **i** `user_permissions` po
  `source_assignment_id`; nadania ręczne (`NULL`) zostają.

**Done gdy:** testy — diakon nie utworzy przypisania typu `pastor` (403); członek zboru nie nada
sobie `bishop` (403); pastor nie nada roli szerszej niż własna (403); usunięcie służby czyści
dokładnie swoje wiersze ACL.

---

### T9 · Governance API

**Pliki:** `backend/app/modules/churches/router.py`, `schemas.py`

- `POST /churches` za `church.create`. Biskup regionalny: `region_id` **wymuszony** na jego rejon
  (inny rejon → 403); admin może utworzyć bez rejonu, odpowiedź niesie ostrzeżenie.
- `PATCH /churches/{church_id}/region` za `church.move_region` (tylko `bishop` i admin).
  Po zmianie **bump `acl:epoch`** — zmiana rejonu przebudowuje łańcuchy zasięgów (architektura §7).
- `POST /tenants` (`tenants/router.py`) — bramka `church.create` już jest (commit `8b2f32f`),
  przepiąć na `PermissionService`.

**Done gdy:** testy — RB tworzy w swoim rejonie (201) i nie tworzy w cudzym (403); `move_region`
tylko dla biskupa naczelnego/admina; po `move_region` biskup nowego rejonu ma dostęp od razu
(cache unieważniony).

---

## Faza C — widoczność (#008)

### T10 · Backfill `churches.visibility`

**Pliki:** `backend/migrations/080_backfill_church_visibility.py` (nowy)

- Mapowanie z #008: `address.status` `published` / `published_unverified` → `public`;
  `draft` / `need_verification` → `hidden`. Zbory bez adresu → `hidden`.
- **To musi wejść przed T11.** `churches.visibility` ma default `hidden` (`db_models.py:59`) —
  przełączenie filtra publicznej listy bez backfillu wyczyści publiczny katalog zborów.
- Migracja wypisuje liczby przed i po.

**Done gdy:** liczba zborów `visibility = 'public'` po migracji równa się liczbie zborów zwracanych
dziś przez `GET /congregations/detailed`.

---

### T11 · Publiczna lista i publikacja na `churches.visibility`

**Pliki:** `backend/app/modules/tenants/repositories.py`, `backend/app/modules/tenants/router.py`,
`backend/app/modules/churches/router.py`

- `list_published` (`tenants/repositories.py:48`) → filtr po `churches.visibility = 'public'`
  zamiast `tenant.status`.
- `PATCH /churches/{church_id}/visibility` za `church.publish`.
- `address.status` **zostaje** jako workflow redakcyjny — badge `need_verification` w adminie
  niezależny od widoczności.
- Toggle publikacji na stronie edycji zboru przestawia `churches.visibility`, nie `tenant.status`.

**Done gdy:** test gość / zalogowany / pastor widzą różne zestawy pól na
`GET /congregations/detailed`; zbór `hidden` nie pojawia się dla gościa; liczba pozycji
w publicznej liście nie zmienia się po przełączeniu (porównanie przed/po na bazie testowej).

---

### T12 · `GET /me/permissions` + gating na froncie

**Pliki:** `backend/app/modules/churches/router.py`,
`src/shared/composables/usePermissions.ts`, `src/modules/congregations/**`

- `GET /me/permissions` → `{ isAdmin, isOwner, scopes: [{ scopeType, scopeId, permissions[] }] }`.
- `usePermissions()` dostaje `can(permission: string, churchId?: string): boolean`; dane przez
  TanStack Query ze `staleTime` zbliżonym do TTL cache'a ACL (5 min).
- Przyciski edycji / dodawania osób / publikacji chowane wg `can(...)` zamiast
  `authStore.user?.isAdmin` (m.in. `ChurchPeopleSection.vue:115`).
- Konwencje frontu: `<script setup lang="ts">`, jawne generyki `ref<T>` / `computed<T>`, brak
  średników (CLAUDE.md).

**Done gdy:** `pnpm type-check` i `pnpm lint` czyste; test vitest, że komponent chowa akcję bez
uprawnienia; API dalej odrzuca żądanie niezależnie od stanu UI.

---

## Czego ten plan nie obejmuje

| Element | Gdzie |
|---|---|
| Publiczne URL-e `/kraj/miasto/slug`, aliasy, 301 | [#009](../issues/2026-07-09--009--public-hierarchical-urls.md) |
| UI governance, picker uprawnień, invite flow, audit log | [#010](../issues/2026-07-09--010--church-governance-actions.md) |
| `finances.manage` | odłożone (architektura §4) |
| Nadpisywanie roli per przypisanie, `probation_ends_at` | poza MVP |
| Usunięcie `tenants` / `tenant_memberships` | zostają jako infrastruktura |
