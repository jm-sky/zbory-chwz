# Architektura ACL — platforma zborów CHWZ

**Status:** `planned`
**Created:** 2026-07-25
**Zastępuje (dla Fazy 2):** sekcję „2. Służby, People i ACL" w [church-platform-implementation.md](./2026-07-09--church-platform-implementation.md)
**Plan zadań:** [2026-07-25--acl-implementation-tasks.md](./2026-07-25--acl-implementation-tasks.md)
**Issues:** [#007](../issues/2026-07-09--007--acl-roles-permissions.md) · [#008](../issues/2026-07-09--008--visibility-layer.md) · [#010](../issues/2026-07-09--010--church-governance-actions.md)
**Review odniesienia:** [2026-07-10--church-platform-review.md](../reviews/2026-07-10--church-platform-review.md)

---

## Po co ten dokument

Plan z 2026-07-09 opisał ACL na poziomie tabel i listy uprawnień, ale nie rozstrzygnął algorytmu
rozwiązywania uprawnień ani reguł nadawania ról. Faza 1 (model danych) została dowieziona, Faza 2
nie — a kod w międzyczasie dostał kilka punktowych łatek autoryzacyjnych. Ten dokument domyka
projekt warstwy uprawnień na tyle, żeby dało się ją zaimplementować bez kolejnych decyzji
produktowych.

### Stan faktyczny (zweryfikowany w kodzie 2026-07-25)

| Element | Stan |
|---|---|
| Hierarchia `communities → regions → churches → branches` | ✅ `backend/app/modules/churches/db_models.py` |
| `persons`, `service_types`, `service_assignments`, aliasy slugów | ✅ tamże, migracje 056–059 |
| Tabele ACL `roles` / `role_permissions` / `user_role_assignments` | ✅ `churches/acl_models.py` |
| `VisibilityService` + enum `hidden\|public\|authenticated\|pastors` | ✅ `churches/visibility.py` |
| Punktowe użycia ACL (`persons/search`, `POST /tenants`, karta zboru) | ✅ commit `8b2f32f` |
| `PermissionService.resolve(user, permission, scope)` | ❌ nie istnieje |
| `user_permissions` (wyjątki allow/deny) | ❌ nie istnieje |
| Autoryzacja zapisów zborowych | ❌ `_verify_church_access` (`churches/router.py:34`) i `verify_tenant_access` (`tenants/access.py`) patrzą **wyłącznie na członkostwo w tenancie** — dowolny `member` edytuje placówki, ludzi i służby |
| „Diakon nie nadaje służb pasterskich" (P-2 z review) | ❌ brak |
| Governance API (`POST /churches`, `PATCH .../region`) | ❌ brak |
| Publiczna lista po `churches.visibility` (P-6) | ❌ dalej `tenant.status` (`tenants/repositories.py:48`) |

---

## 1. Cztery rozdzielone warstwy

```
struktura organizacyjna   communities → regions → churches → branches
służba (funkcja)          service_assignments          — NIE daje uprawnień
uprawnienia (ACL)         roles + user_role_assignments + user_permissions
widoczność (odczyt)       visibility: hidden | public | authenticated | pastors
```

Reguła nadrzędna, z której wynika cała reszta:

> **Służba ≠ uprawnienia.** `service_types.suggested_role` jest podpowiedzią dla UI przy tworzeniu
> konta — nigdy automatycznym nadaniem ACL.

Widoczność (kto **widzi**) jest niezależna od uprawnień (kto **zmienia**). Sprawdzenie widoczności
wykonuje się przed sprawdzeniem uprawnień na endpointach odczytu.

---

## 2. Algorytm rozwiązywania uprawnień

```python
PermissionService.resolve(user, permission, scope: tuple[str, str]) -> bool
```

1. **Globalny override:** `user.isAdmin or user.isOwner` → `allow`. Sprawdzane pierwsze, nie
   podlega wyjątkom `deny`.
2. **Łańcuch zasięgów** od najwęższego do najszerszego:

   ```
   branch  → church → region → community
   church  → region → community
   region  → community
   community
   ```

   `churches.region_id` jest nullowalne (`db_models.py:56`), więc łańcuch potrafi pomijać region.
3. **Snapshot użytkownika:** jednym zapytaniem (albo z cache'a — §6) pobierz wszystkie
   `user_role_assignments` rozwinięte przez `role_permissions` oraz wszystkie `user_permissions`.
   Odfiltruj do zasięgów należących do łańcucha.
4. **`deny` wygrywa:** jeśli w łańcuchu istnieje `user_permissions` z `effect = 'deny'` dla tego
   uprawnienia — `deny`, niezależnie od ról i od `allow` na węższym poziomie.
5. W przeciwnym razie `allow`, jeśli którakolwiek rola albo wyjątek `allow` w łańcuchu daje to
   uprawnienie.

### Świadome uproszczenia

**`deny` globalny w łańcuchu, nie „najbliższy wygrywa".** Nie da się nadpisać szerokiego `deny`
węższym `allow`. Traci się elastyczność („zabroń w całym rejonie, ale pozwól w jednym zborze"),
zyskuje przewidywalność — użytkownik z `deny` nie ma uprawnienia, kropka. Realne przypadki CHWZ
tego nie potrzebują; gdyby zaczęły, zmiana dotyka jednej funkcji i jej testów.

**Brak dziedziczenia „w dół" przy odczycie zasięgu.** Rola na zasięgu `church` nie daje niczego na
`region`. Dziedziczenie idzie wyłącznie od szerszego do węższego.

### Konsekwencja: fallback biskupa naczelnego nie wymaga kodu

Plan przewidywał specjalny przypadek „rejon bez `biskup_regionu` → biskup naczelny przejmuje
uprawnienia rejonowe". Przy chodzeniu po łańcuchu to wychodzi samo: rola na zasięgu `community`
jest przodkiem każdego rejonu i każdego zboru. **Żadnego kodu fallbacku nie piszemy** — i nie
wolno go dopisać, bo tworzyłby drugą, rozjeżdżającą się ścieżkę decyzyjną.

### Pułapka: zbór bez rejonu

`provisioning.py:68` tworzy zbory z `region_id = None`, a backfill przypisuje rejon tylko wg mapy
miast (`seed_data.py: CITY_REGION_MAP`). Zbór z `region_id = NULL` jest **niewidoczny dla biskupa
regionalnego** — jego łańcuch to `church → community`. To nie jest błąd algorytmu, tylko brakujące
dane. Governance musi tego pilnować:

- `POST /churches` wykonane przez biskupa regionalnego **wymusza** `region_id` = jego rejon;
- admin tworzący zbór bez rejonu dostaje ostrzeżenie w odpowiedzi (nie błąd);
- raport „zbory bez rejonu" w CLI/adminie jako zadanie porządkowe.

---

## 3. Trzy kształty zapytań, jedna implementacja łańcucha

| Metoda | Zastosowanie | Uwagi |
|---|---|---|
| `resolve(user, permission, scope)` | autoryzacja konkretnego obiektu | rdzeń, §2 |
| `has_anywhere(user, permission)` | endpointy bez obiektu docelowego (`GET /churches/persons/search`, `POST /churches`) | zastępuje dzisiejsze `AclService.has_permission` (`acl_service.py:19`); semantyka: istnieje zasięg, w którym `resolve` dałoby `allow` |
| `allowed_church_ids(user, permission)` | filtrowanie list i eksportów | `None` = bez ograniczeń (admin/owner), pusty zbiór = brak dostępu |

`allowed_church_ids` to **uogólnienie istniejącego** `DirectoryRepository.get_allowed_church_ids`
(`directory/repositories.py:41`), które dziś ignoruje uprawnienie i traktuje *dowolną* rolę
w dowolnym zasięgu jako dostęp do kontaktów. Logika rozwijania zasięgów (region/community → zbiór
`church_id`) jest tam już poprawna — należy ją przenieść do `PermissionService`, dołożyć filtr po
uprawnieniu, a `DirectoryRepository` ma wołać serwis zamiast trzymać własną kopię.

---

## 4. Katalog uprawnień (MVP)

| Uprawnienie | Znaczenie |
|---|---|
| `church.view` | podgląd profilu zboru w panelu (z uwzględnieniem widoczności) |
| `church.view_pastoral` | dostęp do treści na poziomie widoczności `pastors` |
| `church.edit` | edycja profilu, adresu, godzin nabożeństw |
| `church.create` | utworzenie zboru |
| `church.delete` | soft delete zboru |
| `church.publish` | zmiana `churches.visibility` |
| `church.move_region` | przeniesienie zboru między rejonami |
| `services.manage` | przypisania służb (w tym pasterskich) i nadawanie ról ACL |
| `people.manage` | osoby i przypisania nie-pasterskie, widoczność kontaktów |
| `branch.manage` | zarządzanie placówką |
| `events.manage` | zarezerwowane (moduł wydarzeń) |
| `documents.manage` | zarezerwowane (moduł dokumentów) |

### Dwa nowe uprawnienia względem planu z 2026-07-09

**`church.view_pastoral`** — dziś poziom widoczności `pastors` jest liczony przez dopasowanie
po **nazwach ról**: `AclService.has_pastoral_access` (`acl_service.py:39`) sprawdza
`RoleDB.name in PASTORAL_ROLE_NAMES` (`acl_seed.py:11`). To druga, równoległa implementacja
chodzenia po zasięgach i osobne źródło prawdy o tym, „kto jest pastorem". Zastępujemy je zwykłym
uprawnieniem: `pastors` = `resolve(user, "church.view_pastoral", church)`. Jedna implementacja
łańcucha, a zestaw uprawnionych da się zmienić seedem zamiast edycją frozensetu w kodzie.

**`church.publish`** — kto przestawia zbór na `visibility = public`. Nadane rolom `pastor`,
`regional_bishop`, `bishop`: pastor odpowiada za dane własnego zboru, więc odpowiada też za ich
publikację. Decyzja odwracalna — gdyby publikacja miała wymagać akceptacji biskupa, wystarczy
zdjąć uprawnienie roli `pastor` w seedzie.

### Poza MVP

**`finances.manage`** — odpowiedź na open question z #007: **później**, nie w tej serii. String
zarezerwowany, żadna rola go nie dostaje. Przypadek „diakon-skarbnik" obsługuje na razie
`service_types.diakon_skarbnik` (służba organizacyjna, `seed_data.py`) bez odpowiednika w ACL.

### Domyślne mapowanie ról

| Rola | Zasięg | Uprawnienia |
|---|---|---|
| `bishop` | `community` | `church.view`, `church.view_pastoral`, `church.edit`, `church.create`, `church.delete`, `church.publish`, `church.move_region`, `services.manage`, `people.manage`, `branch.manage` |
| `regional_bishop` | `region` | jak wyżej **bez** `church.move_region` i `church.delete` |
| `pastor` | `church` | `church.view`, `church.view_pastoral`, `church.edit`, `church.publish`, `people.manage`, `branch.manage`, `events.manage` |
| `diacon` | `church` | `church.view`, `church.view_pastoral`, `church.edit`, `people.manage`, `events.manage` |
| `branch_responsible` | `branch` | `church.view`, `branch.manage` |
| admin / owner | globalny | wszystko (override poza tabelami) |

Różnica wobec dzisiejszego `ROLE_SEED` (`acl_seed.py:17`): dochodzą `church.view_pastoral`,
`church.publish`, `church.delete`, `branch.manage` i rola `branch_responsible`. `diacon` **nie ma**
`services.manage` — to podstawa reguły z §5.2.

> **Uwaga implementacyjna:** `ensure_acl_roles` (`acl_seed.py:61`) dokłada uprawnienia **tylko przy
> tworzeniu nowej roli**. Na bazie, gdzie role już istnieją, nowe permissiony nigdy się nie pojawią.
> Do naprawy razem z rozszerzeniem seeda (zadanie T2).

---

## 5. Reguły nadawania uprawnień i przypisywania służb

### 5.1. Nadawanie ról ACL — zasada zamiast łatki

Review z 2026-07-10 (SEC-2) opisał eskalację do roli `bishop` przez pole `suggestedRole`
w payloadzie. Doraźna łatka to `can_grant_elevated_roles = current_user.isAdmin or isOwner`
(`repositories.py:356`, `_resolve_grant_role`). Docelowo trzy niezmienniki:

1. **Bez eskalacji:** można nadać wyłącznie rolę, której zbiór uprawnień jest **podzbiorem**
   uprawnień nadającego w tym zasięgu. Sam z siebie zamyka całą klasę ataków, nie tylko `bishop`.
2. **Autoryzacja nadania:** nadający musi mieć `services.manage` w zasięgu nadania.
3. **Twarda bramka na role ponad-zborowe:** `bishop` i `regional_bishop` nadaje wyłącznie
   admin/owner albo posiadacz `services.manage` na zasięgu `community`.

Punkt 3 jest formalnie nadmiarowy wobec 1+2, ale zostaje jako jawna bariera — łatwiej ją
przetestować i trudniej znieść przypadkiem przy zmianie seeda.

### 5.2. Kto może przypisać jaką służbę (P-2)

Wymagane uprawnienie zależy od typu przypisywanej służby:

```python
required_permission_for_service_type(service_type) -> tuple[str, str | None]
# -> (permission, wymagany_zasięg lub None dla „dowolny w łańcuchu")
```

| `service_types.suggested_role` | Wymagane |
|---|---|
| `bishop`, `regional_bishop` | `services.manage` **na zasięgu `community`** |
| `pastor` | `services.manage` (biskup, biskup regionalny we własnym rejonie, admin) |
| `diacon`, `NULL`, służba custom (`custom_service_name`) | `people.manage` |

Diakon ma `people.manage`, nie ma `services.manage` → nie przypisze pastora ani biskupa, ale
obsłuży zwykłe osoby kontaktowe. Ta sama funkcja obsługuje `POST`, `PATCH` i `DELETE`
przypisania — przy zmianie typu służby sprawdzana jest wartość **starsza i nowa** (inaczej
podniesienie „członek rady" → „pastor" omijałoby regułę).

### 5.3. Kasowanie ACL przy odejściu ze służby

Bez zmian wobec planu: `user_role_assignments.source_assignment_id` i (nowo)
`user_permissions.source_assignment_id` kaskadują z `ON DELETE CASCADE` na `service_assignments`.
Usunięcie przypisania czyści **tylko** wiersze pochodzące z tego przypisania — nadania ręczne
(`source_assignment_id IS NULL`) zostają.

---

## 6. Schemat `user_permissions`

```sql
CREATE TABLE user_permissions (
  id                   VARCHAR(36) PRIMARY KEY,
  user_id              VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope_type           VARCHAR(32) NOT NULL,   -- community | region | church | branch
  scope_id             VARCHAR(36) NOT NULL,
  permission           VARCHAR(64) NOT NULL,
  effect               VARCHAR(8)  NOT NULL,   -- allow | deny
  source_assignment_id VARCHAR(36) REFERENCES service_assignments(id) ON DELETE CASCADE,
  created_by           VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, scope_type, scope_id, permission)
);
CREATE INDEX ix_user_permissions_user_id ON user_permissions (user_id);
CREATE INDEX ix_user_permissions_source_assignment_id ON user_permissions (source_assignment_id);
```

`UNIQUE` **bez** `effect` — jeden wiersz na trójkę (user, zasięg, uprawnienie), więc `allow`
i `deny` nie mogą współistnieć i nie trzeba rozstrzygać remisu.

`created_by` jest po to, żeby dało się odpowiedzieć „kto to nadał" bez pełnego audit logu
(audit log zostaje w #010).

**UI na MVP:** picker przy „Utwórz konto" pokazuje **tylko wybór roli** — odpowiedź na open
question z #007. Wyjątki `allow`/`deny` są dostępne wyłącznie dla admina (na start przez CLI).
Model wchodzi od razu, żeby nie przepisywać resolvera, gdy wyjątki będą potrzebne.

---

## 7. Cache

- Redis (klient gotowy: `backend/app/core/redis.py`), klucz `acl:v{epoch}:{user_id}`.
- Cache'owany jest **snapshot grantów użytkownika** (role rozwinięte do uprawnień + wyjątki),
  nie odpowiedzi per `(permission, scope)`. Jeden round-trip na request niezależnie od liczby
  sprawdzeń; łańcuch zasięgów liczony w procesie.
- TTL 300 s.
- **Inwalidacja per user:** zmiana `user_role_assignments`, zmiana `user_permissions`, usunięcie
  `service_assignment` powiązanego z ACL.
- **Globalny `acl:epoch`** (bump = unieważnienie wszystkich): zmiana `role_permissions` / seed ról,
  zmiana `churches.region_id` lub `churches.community_id`. Zmiana rejonu przebudowuje łańcuchy
  wszystkim, jest rzadka, więc globalny bump jest tańszy niż śledzenie zależności.
- **Redis niedostępny → zapytanie do bazy.** Fallback, nie fail-closed: brak cache'a ma degradować
  wydajność, nie odbierać ludziom dostępu.

---

## 8. Integracja z FastAPI

```python
@router.patch("/{church_id}", dependencies=[RequirePermission("church.edit")])
```

- `get_permission_service()` — DI w konwencji istniejącego `get_acl_service` (`acl_service.py:68`).
- `RequirePermission(permission, *, param="church_id", scope_type="church")` — fabryka zależności
  czytająca parametr ścieżki.
- **Wariant `tenant_id`:** `churches.id == tenants.id` z konstrukcji (`provisioning.py:66`,
  `backfill.py:71`), więc resolver mapuje 1:1. Musi jednak **odrzucić organizacyjny tenant CHWZ**
  (`seed_data.CHWZ_ORG_TENANT_NAME`), który nie ma wiersza w `churches`.
- **Kody odpowiedzi:** `404` gdy zbór nie istnieje, `403` gdy istnieje a brak uprawnień — zgodnie
  z istniejącymi testami (`backend/tests/integration/congregations/test_congregations_authz.py`).
  Nie maskujemy istnienia zboru pod `404`: identyfikatory zborów są i tak publiczne.

---

## 9. Migracja `tenant_memberships` → ACL

**Decyzja:** ACL jest jedynym źródłem prawdy o uprawnieniach. Członkostwo w tenancie przestaje
dawać prawo zapisu i zostaje wyłącznie jako infrastruktura tenantów (lista „moje zbory", billing).

Ryzyko jest realne — dziś to jedyna ścieżka dostępu pastorów do własnych zborów. Sekwencja
minimalizująca szansę odcięcia kogoś od jego danych:

1. **Migracja danych, idempotentna:**
   - membership `owner` / `admin` na tenancie mającym zbór → rola `pastor` w zasięgu `church`;
   - membership `member` → rola `pastor` **tylko** jeśli ta osoba ma w tym zborze
     `service_assignment` o typie pasterskim (`seed_data.PASTOR_SERVICE_SLUGS`); w przeciwnym razie
     brak nadania — dostęp czytelniczy zostaje przez widoczność;
   - nadania migracyjne mają `source_assignment_id = NULL` (nie pochodzą ze służby, więc nie mogą
     zniknąć przy jej usunięciu).
2. **`python -m cli acl migrate-memberships --dry-run`** — raport „kto co dostanie / kto straci
   dostęp" do przejrzenia przez człowieka **przed** puszczeniem migracji. Bez tego kroku migracji
   nie odpalamy na produkcji.
3. **Przełączenie enforcement:** `verify_tenant_access` (`tenants/access.py`) i
   `_verify_church_access` (`churches/router.py:34`) przechodzą na `PermissionService`.
4. **Shadow log:** każde żądanie odrzucone przez ACL, które przeszłoby po staremu (membership),
   loguje `acl.shadow_deny` z `user_id`, `church_id`, `permission`. Nie zmienia decyzji — daje ops
   sygnał, że migracja kogoś pominęła. Do usunięcia po tygodniu czystych logów.

---

## 10. Widoczność — co zostało do dokończenia (#008)

- **Publiczna lista** filtruje `churches.visibility = 'public'` zamiast `tenant.status`
  (`tenants/repositories.py:48`) / `address.status`.
- **Kolejność krytyczna:** `churches.visibility` ma default `hidden` (`db_models.py:59`).
  Przełączenie filtra bez wcześniejszego backfillu **wyczyści publiczny katalog zborów**.
  Backfill idzie osobną migracją, wg tabeli mapowania z #008 (`published` / `published_unverified`
  → `public`; `draft` / `need_verification` → `hidden`), z zapytaniem zliczającym przed i po.
- `address.status` **zostaje** jako workflow redakcyjny (badge `need_verification` w adminie) —
  zbór może być `visibility = public` z adresem `published_unverified`.
- `PATCH /churches/{id}/visibility` za uprawnieniem `church.publish`.
- `VisibilityService.can_view` (`visibility.py:29`) bez zmian; parametr `has_pastoral_access`
  liczony przez `resolve(user, "church.view_pastoral", church)` — patrz §4.
- **Front:** `GET /me/permissions` zwraca `{scopeType, scopeId, permissions[]}`;
  `usePermissions()` (`src/shared/composables/usePermissions.ts`) dostaje `can(permission, churchId)`.
  Gating na froncie jest wyłącznie UX-owy — autorytetem pozostaje API.

---

## 11. Macierz testów

Podmiot × akcja × zasięg, ~20 przypadków integracyjnych:

| Podmiot | `church.edit` | `services.manage` (pastor) | `services.manage` (diakon) | `church.create` | `church.move_region` | `church.publish` | pola `pastors` |
|---|---|---|---|---|---|---|---|
| gość | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| zalogowany bez roli | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| diakon własnego zboru | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ |
| pastor własnego zboru | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| pastor obcego zboru | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| biskup regionalny, zbór w rejonie | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| biskup regionalny, zbór poza rejonem | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| biskup naczelny (community) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| admin / owner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Przypadki brzegowe do osobnych testów:

- wyjątek `deny` na zasięgu `community` bije rolę `pastor` na zasięgu `church`;
- usunięcie `service_assignment` kasuje wiersze ACL o tym `source_assignment_id`, zostawia nadania
  ręczne (`NULL`);
- zbór z `region_id = NULL` — biskup regionalny **nie** ma do niego dostępu, biskup naczelny ma;
- rejon bez przypisanego `biskup_regionu` — biskup naczelny działa bez kodu fallbacku;
- organizacyjny tenant CHWZ odrzucony przez resolver `tenant_id → church_id`;
- nadanie roli spoza własnego zbioru uprawnień → `403` (reguła podzbioru, §5.1);
- Redis wyłączony → wyniki identyczne jak z cache'em.

---

## 12. Poza zakresem

- **#009** — publiczne URL-e hierarchiczne (aliasy, city aliases, 301). Niezależne od ACL, odłożone.
- **#010** — UI governance, picker uprawnień, invite flow, audit log. Po wdrożeniu tego dokumentu.
- `finances.manage`, nadpisywanie roli per przypisanie, `probation_ends_at`.
- Usunięcie `tenants` / `tenant_memberships` — zostają jako infrastruktura.

---

## Changelog

| Data | Zmiana |
|---|---|
| 2026-07-25 | Dokument początkowy: algorytm rozwiązywania uprawnień, katalog uprawnień, reguły nadawania, `user_permissions`, cache, migracja membership → ACL |
