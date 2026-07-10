# Review: platforma zborów — zgodność z planem, security, jakość, UX

**Status:** `done`
**Created:** 2026-07-10
**Zakres:** `backend/app/modules/{churches,congregations,tenants}`, `src/modules/congregations`, migracje 056–059
**Plany odniesienia:**
- [church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md)
- [church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)
- [church-platform.md](../plans/2026-07-09--church-platform.md)

---

## Podsumowanie

Faza 1 (model danych) jest zaimplementowana zgodnie z planem: hierarchia `communities → regions → churches → branches`, `persons`, `service_types`, `service_assignments`, aliasy slugów, backfill z `contact_persons`. Migracje 056–059 są idempotentne i mają `downgrade`. Frontend ma sekcję „Ludzie i służby" z widocznością per pole.

**Blokada:** warstwa autoryzacji nie istnieje. `PermissionService` z Fazy 2 nie powstał, a endpointy `/congregations/*` nie mają **żadnego** sprawdzenia dostępu poza „user jest zalogowany". W praktyce dowolne zalogowane konto może edytować adres, godziny nabożeństw i osoby kontaktowe **każdego** zboru. Do tego payload `suggestedRole` pozwala nadać sobie rolę `bishop` w zasięgu całej wspólnoty.

Druga blokada, mniej dotkliwa: `AclService.has_pastoral_access()` nie jest nigdzie wywoływany — jedyne miejsce, które go potrzebuje, przekazuje `has_pastoral_access=False` na sztywno. Poziom widoczności `pastors` jest więc funkcjonalnie równy `hidden`.

| Obszar | Ocena |
|--------|-------|
| Zgodność z planem (Faza 1) | dobra — brakuje UI wyszukiwania osoby |
| Zgodność z planem (Faza 2 ACL) | brak implementacji; tabele są, egzekwowania nie ma |
| Security | **krytyczne braki** (SEC-1…SEC-4) |
| Jakość kodu | średnia — duplikacja serializacji, N+1, martwy kod |
| UX | średnia — brak potwierdzeń, brak wyszukiwarki osób, braki i18n |

---

## Zgodność z planem

### Zrealizowane

| Element planu | Stan |
|---------------|------|
| Tabele `communities`, `regions`, `churches`, `branches` | ✅ `056_create_church_hierarchy.py` |
| `persons`, `service_types`, `service_assignments` | ✅ |
| `church_slug_aliases`, `city_aliases` | ✅ tabele + `slug_utils.py` |
| `church_id` FK na tabelach `congregation_*` | ✅ |
| Reuse `tenant.id` jako `churches.id` | ✅ `backfill.py:65` |
| Seed: wspólnota `chwz`, 4 rejony, typy służb | ✅ `seed_data.py` |
| Backfill `contact_persons` → `service_assignments` | ✅ idempotentny, `source_contact_person_id` |
| Enum widoczności (`hidden/public/authenticated/pastors`) | ✅ `visibility.py` + migracja 058 |
| Tabele ACL (`roles`, `role_permissions`, `user_role_assignments`) | ✅ `059_acl_tables.py` |
| UI: placówki + Ludzie/Służby | ✅ `ChurchBranchesSection.vue`, `ChurchPeopleSection.vue` |
| `GET /persons/search` | ⚠️ endpoint jest, UI go nie używa |

### Rozjazdy z planem

| # | Plan mówi | Kod robi |
|---|-----------|----------|
| P-1 | `PermissionService.resolve(user, permission, scope)` + `RequirePermission(...)` (Faza 2) | Brak. `_verify_church_access` sprawdza tylko „czy user ma jakiekolwiek membership w tenancie" — bez roli, bez permissiona |
| P-2 | „Diakon **nie może** przypisywać typów `biskup_*`, `pastor`, `*_pastor`" | Brak walidacji. Każdy członek zboru może utworzyć przypisanie dowolnego typu |
| P-3 | „Create church: Bishop / Regional Bishop / Admin" | `POST /tenants` (`tenants/router.py:48`) — **dowolny zalogowany user** tworzy tenant i zostaje jego ownerem |
| P-4 | „Change region: Bishop only" | Endpoint `PATCH .../region` nie istnieje. `region_id` ustawia tylko backfill |
| P-5 | Uprawnienia ACL **niezależne** od służby, `suggested_role_id` = tylko podpowiedź UI | Backend przyjmuje `suggestedRole` z payloadu i nadaje rolę bez żadnej weryfikacji, kto nadaje (SEC-2) |
| P-6 | „Public list endpoint: filter `churches.visibility = public`, nie `tenant.status`" | `list_congregations_detailed` filtruje po `address.status`. Kolumna `churches.visibility` istnieje, jest ignorowana |
| P-7 | Wybór istniejącej osoby przez wyszukiwarkę | `churchApiService.searchPersons()` istnieje, żaden komponent go nie woła — zawsze tworzona jest nowa `person` |
| P-8 | „Deprecate API `contact_persons`" (ROADMAP „Pozostało") | Endpointy legacy nadal aktywne i **bez autoryzacji** (SEC-1) |
| P-9 | Cache uprawnień w Redis + inwalidacja | Nie dotyczy — nie ma czego cache'ować |

---

## Findings — Security

### SEC-1 · Krytyczne · Brak autoryzacji na `/congregations/*` (IDOR)

`backend/app/modules/congregations/router.py` — **wszystkie 11 endpointów**. Każdy przyjmuje `current_user: CurrentUser`, po czym nigdy go nie używa. Jedyna weryfikacja to „czy tenant istnieje":

```python
tenant = await tenant_repo.get_tenant(tenant_id)
if not tenant:
    raise HTTPException(404)
# ... i od razu zapis, bez sprawdzenia dostępu
address = await repo.create_or_update_address(tenant_id=tenant_id, ...)
```

**Skutek:** dowolne konto (świeża rejestracja wystarczy) może odczytać, zmienić lub usunąć adres, godziny nabożeństw i osoby kontaktowe każdego zboru w systemie. `tenant_id` jest publiczny — zwraca go `GET /congregations/detailed` jako `id`.

**Fix:** wspólny helper autoryzacji (membership ∨ admin ∨ owner) na każdym endpoincie. *Naprawione w tym przebiegu.*

---

### SEC-2 · Krytyczne · Eskalacja uprawnień przez `suggestedRole`

`churches/schemas.py:89` przyjmuje `suggestedRole: ChurchAclRole | None` od klienta. `repositories.py:225` nadaje tę rolę bez pytania, kto wywołuje:

```python
role_name = payload.suggestedRole or (service_type.suggested_role if service_type else None)
if not role_name or role_name not in PASTORAL_ROLE_NAMES:
    return
# ... UserRoleAssignmentDB(user_id=user_db.id, role_id=role.id, scope_type='community', ...)
```

`resolve_acl_scope("bishop", ...)` mapuje na `scope_type='community'`, a rola `bishop` ma w `acl_seed.py` komplet permissionów (`church.create`, `church.move_region`, `services.manage`, …).

**Ścieżka ataku:** członek dowolnego zboru wywołuje `POST /churches/{id}/service-assignments` z `email` równym **własnemu adresowi** i `suggestedRole: "bishop"`. `_maybe_create_user_and_acl` znajduje istniejące `UserDB` po e-mailu (`repositories.py:201`), podpina je do nowej `person`, i nadaje temu userowi rolę `bishop` w zasięgu całej wspólnoty.

Ten sam mechanizm to **przejęcie konta w drugą stronę**: podanie cudzego e-maila linkuje `person.user_id` do cudzego konta i nadaje mu członkostwo w tenancie atakującego (`_ensure_tenant_membership`).

**Fix (minimalny):** `bishop` / `regional_bishop` może nadać wyłącznie admin/owner. *Naprawione w tym przebiegu.* Docelowo — `PermissionService` + `services.manage` (issue #007).

---

### SEC-3 · Wysokie · `_verify_church_access` jest fail-open

`churches/router.py:34`:

```python
tenant = await tenant_repo.get_tenant(church_id)
if not tenant:
    return          # ← brak tenanta = dostęp przyznany
```

Church bez odpowiadającego wiersza w `tenants` (np. utworzony poza backfillem, albo tenant usunięty przy `ON DELETE CASCADE` niedziałającym na starych danych) staje się edytowalny dla każdego zalogowanego. *Naprawione w tym przebiegu — teraz 403.*

---

### SEC-4 · Średnie · `GET /churches/persons/search` wycieka PII

`churches/router.py:73` — dowolne zalogowane konto odpytuje **globalną** bazę osób po imieniu, nazwisku i e-mailu, bez zawężenia do zborów, do których ma dostęp. `%q%` na trzech kolumnach + `limit 20` to wygodny scraper adresów e-mail wszystkich pastorów i diakonów w CHWZ.

Endpoint nie jest jeszcze używany przez UI, więc ograniczenie go teraz nie psuje niczego. **Do decyzji:** zawęzić do `services.manage` w jakimkolwiek zasięgu, czy do admin/owner. *Nie zmieniam — decyzja produktowa.*

---

### SEC-5 · Średnie · `POST /tenants` bez ograniczeń

`tenants/router.py:48` — każdy zalogowany tworzy „zbór" i zostaje jego ownerem. Plan (§5, governance) rezerwuje tworzenie zborów dla biskupów i admina. Poza obejściem governance to również ścieżka do SEC-2: własny tenant → własny church → własne przypisania.

Admin ma równoległy `POST /admin/tenants`. **Sugestia:** usunąć publiczny `POST /tenants` albo objąć go `church.create`.

---

### SEC-6 · Niskie · Warstwa widoczności nie odróżnia gościa od zalogowanego

`tenants/router.py:132` przekazuje `is_authenticated=False, has_pastoral_access=False` na sztywno. Konsekwencje:

- `AclService` (`churches/acl_service.py`) to martwy kod — nikt go nie instancjonuje,
- poziom `pastors` zachowuje się identycznie jak `hidden`,
- zalogowany pastor nie widzi e-maili oznaczonych `authenticated` (domyślna wartość dla e-maila!) na liście zborów.

To nie jest wyciek — jest odwrotnie, zbyt restrykcyjne. Ale oznacza, że Faza 3 planu jest zaimplementowana tylko w połowie: enum i storage są, egzekwowanie po stronie odczytu nie.

---

## Findings — Poprawność

### BUG-1 · Wysokie · Zapis międzyzborowy w `update_service_assignment` i `update_branch`

`churches/router.py:249`:

```python
assignment = await repo.update_service_assignment(assignment_id, payload)   # ← commit()
if not assignment or assignment.scope_id != church_id:
    raise HTTPException(404)                                                # ← za późno
```

Repo mutuje i commituje **zanim** router sprawdzi, czy przypisanie należy do tego zboru. Członek zboru A wysyła PATCH na `assignment_id` ze zboru B: dostaje 404, ale dane zboru B są już nadpisane (łącznie z `person.email` i `person.phone`, bo `update_service_assignment` edytuje też encję `person`). Identycznie `update_branch` (`router.py:172`).

*Naprawione w tym przebiegu — weryfikacja scope przed mutacją, w repo.*

---

### BUG-2 · Wysokie · Pastor nie może zapisać podstawowych danych zboru

`src/modules/congregations/services/congregationApiService.ts:107`:

```typescript
async updateCongregation(id: string, data: IUpdateCongregationRequest): Promise<void> {
  await apiClient.patch(`/admin/tenants/${id}`, data)
}
```

`PATCH /admin/tenants/{id}` ma dependency `AdminOrOwnerUser`. Zarówno „Zapisz" w sekcji Podstawowe informacje (`EditCongregationPage.vue:130`), jak i „Cofnij publikację" (`CongregationsList.vue:116`) trafiają w ten endpoint. Dla pastora/diakona → 403.

Efekt jest maskowany przez BUG-3: przycisk i tak się nie pokazuje nie-adminom. Ale strona `/congregations/:id/edit` jest osiągalna bezpośrednio z URL, a sekcje Adres / Godziny / Ludzie działają (bo nie mają autoryzacji — SEC-1). Wychodzi z tego zbór, w którym pastor edytuje wszystko poza nazwą i statusem.

**Wymaga decyzji:** dodać `PATCH /congregations/{tenant_id}` (nie-admin, membership + `church.edit`) i przepiąć frontend.

---

### BUG-3 · Średnie · `canManageCongregation()` czyta pole, którego nigdy nie ma

`CongregationsList.vue:87` → `return !!congregation.role`. Lista pochodzi z `GET /congregations/detailed`, a `PublicCongregationResponse` (`tenants/schemas.py:42`) **nie ma pola `role`**. Zawsze `undefined` → dropdown „Edytuj / Cofnij publikację" widzi wyłącznie admin/owner. Pastor nie ma z UI żadnej ścieżki do edycji swojego zboru.

---

### BUG-4 · Średnie · Nie da się wyczyścić e-maila ani telefonu osoby

`ChurchPeopleSection.vue:221` wysyła `email: editForm.value.email || undefined`. Pusty string → `undefined` → pole pomijane w JSON. Backend (`repositories.py:371`) ma `if payload.email is not None`. Skasowanie e-maila w formularzu nie robi nic — po reloadzie stara wartość wraca.

Ten sam problem dotyczy `phone`, `description`, `customServiceName`. Poprawne rozwiązanie to `null` w payloadzie + rozróżnienie „brak klucza" od „null" po stronie Pydantic (np. `model_fields_set`).

---

### BUG-5 · Średnie · `saveServiceTimes()` — destrukcyjny zapis bez transakcji

`EditCongregationPage.vue:176`:

```typescript
for (const st of currentServiceTimes) {
  await congregationApiService.deleteServiceTime(congregationId, st.id)
}
for (const st of serviceTimeFields.value) {
  await congregationApiService.createServiceTime(congregationId, { ... })
}
```

Delete-all-then-recreate, N+M requestów, bez transakcji. Błąd sieci po pętli kasującej = utrata wszystkich godzin nabożeństw. Dodatkowo nowe wiersze dostają nowe `id`, więc każdy zapis unieważnia ewentualne referencje.

**Sugestia:** `PUT /congregations/{tenant_id}/service-times` przyjmujący całą listę, jedna transakcja po stronie backendu.

---

### BUG-6 · Niskie · `delete_service_time` / `delete_contact_person` nie sprawdzają przynależności

`congregations/router.py:279` i `:448` — kasują po samym `id`, bez `AND tenant_id = ...`. W połączeniu z SEC-1 daje to kasowanie cudzych rekordów. Po naprawie SEC-1 zostaje możliwość skasowania rekordu innego zboru przez członka zboru, do którego się ma dostęp.

---

### BUG-8 · Wysokie · Usunięcie zboru w panelu admina zwracało 500

`admin/router.py` robił `await repo.db.delete(tenant)`. `tenant_memberships.tenant_id` ma FK z `ON DELETE NO ACTION`, a każdy zbór ma co najmniej wpis właściciela — hard delete kończył się `ForeignKeyViolationError`. Gdyby FK nie zablokowało, `churches`, `congregation_addresses`, `congregation_service_times` i `congregation_contact_persons` mają `ON DELETE CASCADE` — zbór zniknąłby razem z całą historią.

Sprawdzone na produkcyjnych danych (34 zbory, 34 membershipy):

```
DELETE FAILED: IntegrityError
ForeignKeyViolationError: update or delete on table "tenants" violates
foreign key constraint "tenant_memberships_tenant_id_fkey"
```

*Naprawione:* migracja `060` dodaje `tenants.deleted_at`; DELETE ustawia znacznik i `status='draft'`, dane zostają. Nowy `POST /admin/tenants/{id}/restore` i `GET /admin/tenants?include_deleted=true` dopełniają cykl. Wszystkie odczyty (`list_all`, `list_published`, `list_for_user`, `get_tenant`) pomijają usunięte, więc zbór znika też z listy publicznej i z `verify_tenant_access`.

---

### BUG-9 · Wysokie · Nowy zbór nie miał wiersza `churches`

`POST /admin/tenants` tworzył wyłącznie `tenants` + membership. `backfill.py` zakłada wiersze `churches` dla zborów sprzed hierarchii, ale nic nie robiło tego dla zborów tworzonych w runtime. Skutek: po dodaniu zboru w panelu jego strona edycji rozsypywała się — `GET /churches/{id}/branches` i `.../service-assignments` zwracały 404 „Church not found".

*Naprawione:* `churches/provisioning.py` → `provision_church_for_tenant()` (idempotentne, reużywa `tenant.id` jako `churches.id`, `region_id` zostaje NULL do przypisania przez biskupa). Wołane z `create_tenant_admin`.

---

### BUG-10 · Wysokie · Cztery schematy odpowiedzi rzucały `ValidationError` (500)

`BranchResponse`, `ChurchResponse`, `RegionResponse` i `PersonResponse` deklarują `Field(validation_alias="church_id")` itd., ale **nie** mają `populate_by_name=True`. Router konstruował je po nazwach pól:

```python
return BranchResponse(id=branch.id, churchId=branch.church_id, ...)
# pydantic_core.ValidationError: 2 validation errors for BranchResponse
#   church_id: Field required
#   created_at: Field required
```

Czyli **500** na: `POST/PATCH /churches/{id}/branches`, `GET /churches/{id}`, `GET /churches/regions`, `GET /churches/persons/search`, oraz `GET /churches/{id}/branches` gdy jakakolwiek placówka istnieje. Nie wyszło wcześniej, bo w bazie nie ma jeszcze żadnej placówki, a lista pusta nie konstruuje modelu.

Znalezione przez faktyczne wywołanie endpointów, nie przez czytanie kodu — typy przechodzą, testów nie było.

*Naprawione:* wszystkie sześć miejsc używa `model_validate(obj)`, zgodnie z `ServiceAssignmentResponse` i `ServiceTypeResponse`. Przy okazji realizuje Q-2.

---

### BUG-7 · Niskie · `ensure_acl_roles()` nie uzupełnia permissionów istniejących ról

`acl_seed.py:56` — `if not role:` tworzy rolę **wraz z** permissionami. Jeśli rola już istnieje, `ROLE_SEED` jest ignorowany. Dopisanie nowego permissiona do `ROLE_SEED` nie zadziała na środowisku, gdzie role już powstały. Migracja 059 seeduje tabele, więc w praktyce ta ścieżka jest martwa — ale to pułapka na przyszłość.

---

## Findings — Jakość kodu

| # | Plik | Uwaga |
|---|------|-------|
| Q-1 | `tenants/router.py:110` | **N+1**: pętla po wszystkich tenantach × 3 zapytania (address, service_times, assignments). Przy 100 zborach → 301 round-tripów na każde wejście na stronę główną. `selectinload` + jedno zapytanie z joinem |
| Q-2 | `congregations/router.py` | 11 endpointów × ręczne przepisywanie 9 pól z modelu do schematu. `ConfigDict(from_attributes=True)` + `model_validate` usuwa ~200 linii |
| Q-3 | `congregations/router.py:150,380,408` | `from datetime import ...` i `from sqlalchemy import select` **wewnątrz funkcji**. Import na górze |
| Q-4 | `churches/acl_service.py` | Cały plik to martwy kod (SEC-6) |
| Q-5 | `churches/router.py:200` | `def _assignment_response(assignment)` — brak adnotacji typu; mypy tego nie złapie, bo to argument bez typu |
| Q-6 | `ChurchPeopleSection.vue:87` | `roleOptions` iteruje po `serviceTypes`, żeby dodać role, które już wszystkie są w `CHURCH_ACL_ROLES`. Pętla nic nie wnosi |
| Q-7 | `ChurchPeopleSection.vue` | 574 linie, dwa niemal identyczne formularze (dodawanie + dialog edycji). Prosi się o `<PersonForm>` |
| Q-8 | `EditCongregationPage.vue:55` | Jeden `useForm` dla trzech niezależnych sekcji — submit adresu waliduje też `name` z sekcji wyżej |
| Q-9 | `churches/db_models.py` | `started_at`, `ended_at`, `probation_ends_at` w modelu; żaden endpoint ich nie ustawia ani nie zwraca |
| Q-10 | `backend/tests/` | Zero testów dla `churches/router.py`. Plan wymaga „integration test matrix: (role × action × in/out of scope) — 15–20 cases". Istnieją tylko `test_visibility.py` (czysta funkcja) i `test_church_slug_utils.py` |
| Q-11 | `backend/tests/test_convert_empty_strings_middleware.py` | 2 testy failują na `develop` (`test_handles_invalid_json_gracefully`, `test_handles_non_json_content_type`) — regres niezwiązany z tym modułem |

---

## Findings — UX

| # | Miejsce | Uwaga |
|---|---------|-------|
| U-1 | `ChurchPeopleSection.vue:375`, `ChurchBranchesSection.vue` | Kosz kasuje **bez potwierdzenia**. `CongregationsList` używa `confirm()` przy cofnięciu publikacji — kasowanie osoby jest bardziej destrukcyjne. *Naprawione* |
| U-2 | `pl.ts:106` | Literówka: „Poka**z** na wizytówce" → „Pokaż". *Naprawione* |
| U-3 | `i18n/locales/{pl,en}.ts` | Klucze `congregations.branches.*` **nie istnieją** w żadnym locale. Sekcja placówek działa wyłącznie na fallbackach `t(key, 'polski tekst')` — angielski UI pokazuje polskie napisy. *Naprawione* |
| U-4 | `ChurchPeopleSection.vue` | Brak wyszukiwarki istniejącej osoby (P-7). Pastor w dwóch zborach = dwie osobne `person`. Model to przewiduje, UI nie |
| U-5 | `ChurchPeopleSection.vue:479` | „Dodaj osobę" nie waliduje nic po stronie klienta. Kliknięcie z pustym formularzem → 400 z backendu jako toast |
| U-6 | `ChurchPeopleSection.vue:461` | Select „Uprawnienia" pokazuje `bishop` i `regional_bishop` każdemu edytorowi. Po naprawie SEC-2 backend to odrzuci — UI powinien te opcje ukrywać nie-adminom |
| U-7 | `EditCongregationPage.vue` | Trzy osobne przyciski „Zapisz" bez wskaźnika stanu (dirty / saved). Sekcje Ludzie i Placówki zapisują natychmiast — niespójny model interakcji na jednej stronie |
| U-8 | `pl.ts:107`, `en.ts:107` | Martwe klucze `visibilityPublic` / `visibilityPrivate` po migracji na enum. *Naprawione* |
| U-9 | `CongregationsList.vue` | Zalogowany użytkownik widzi dokładnie to, co gość (SEC-6). E-mail z domyślną widocznością `authenticated` nie pokaże się nigdy i nikomu |

---

## Naprawione w tym przebiegu

| ID | Zmiana |
|----|--------|
| BUG-8 | Soft delete zboru (migracja `060`) + restore + `include_deleted` — hard delete zwracał 500 |
| BUG-9 | `provision_church_for_tenant()` przy tworzeniu zboru |
| BUG-10 | `model_validate` zamiast konstrukcji po nazwach pól — 6 endpointów zwracało 500 |
| SEC-1 | `_verify_tenant_access()` na wszystkich 11 endpointach `/congregations/*` |
| SEC-2 | `bishop` / `regional_bishop` nadaje wyłącznie admin/owner |
| SEC-3 | `_verify_church_access` → 403 zamiast fail-open |
| BUG-1 | Weryfikacja scope **przed** mutacją w `update_service_assignment` / `update_branch` |
| BUG-6 | `delete_service_time` / `delete_contact_person` filtrują po `tenant_id` |
| U-1 | Potwierdzenie przed usunięciem osoby i placówki |
| U-2 | Literówka „Pokaz" → „Pokaż" |
| U-3 | Klucze i18n `congregations.branches.*` (pl + en) |
| U-8 | Usunięte martwe klucze i18n |
| Q-6 | Usunięta martwa pętla w `roleOptions` |

---

## Do omówienia (nie ruszam bez decyzji)

1. **`PermissionService` (issue #007)** — bez niego każde „naprawione" miejsce to łata na membership, a nie na uprawnienia. Blokuje P-1, P-2, P-4, BUG-2. Największa pojedyncza pozycja.
2. **BUG-2 / BUG-3** — potrzebny endpoint `PATCH /congregations/{tenant_id}` dla nie-adminów + `role` w odpowiedzi listy. Bez tego pastor nie zarządza swoim zborem z UI.
3. **SEC-4** — zakres `persons/search`: admin/owner czy `services.manage`?
4. **SEC-5** — usunąć `POST /tenants` czy objąć go `church.create`?
5. **SEC-6 / U-9** — czy publiczna lista ma mieć wariant dla zalogowanych (`GET /congregations/detailed` z opcjonalnym tokenem)? To warunek, żeby poziom `pastors` cokolwiek znaczył.
6. **P-6** — przełączenie filtra publicznej listy z `address.status` na `churches.visibility`.
7. **BUG-5** — `PUT /service-times` (bulk) zamiast delete-all + recreate.
8. **Q-1** — N+1 na stronie głównej; przy obecnej liczbie zborów niegroźne, przy 100+ już tak.
9. **Q-10** — macierz testów autoryzacji. Bez niej regres w ACL przejdzie niezauważony.
10. **Q-11** — dwa czerwone testy middleware na `develop`.
