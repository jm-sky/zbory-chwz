# Hardening autoryzacji — decyzje do podjęcia

**Status:** `done` (2026-07-25)
**Created:** 2026-07-10
**Commit:** `8b2f32f`
**Component:** `churches/router.py`, `tenants/router.py`, `churches/acl_service.py`
**Related:** [#007](./2026-07-09--007--acl-roles-permissions.md) · [#008](./2026-07-09--008--visibility-layer.md) · [review 2026-07-10](../reviews/2026-07-10--church-platform-review.md) (SEC-4, SEC-5, SEC-6)

## Kontekst

Review z 2026-07-10 zamknął krytyczne dziury (IDOR na `/congregations/*`, eskalacja do `bishop` przez `suggestedRole`, zapis międzyzborowy). Zostały trzy pozycje wymagające **decyzji produktowej**, nie samego kodu.

## SEC-4 — zakres `GET /churches/persons/search`

Dziś: dowolne zalogowane konto przeszukuje globalną bazę osób po imieniu, nazwisku i e-mailu. To scraper adresów wszystkich pastorów i diakonów CHWZ. Endpoint nie jest jeszcze używany przez UI.

**Decyzja:** posiadacze `services.manage` w jakimkolwiek zasięgu, dodatkowo ograniczeni do własnych
zborów przez `get_allowed_church_ids`. Admin/owner bez ograniczeń.

- [x] Wybrać zakres i wdrożyć — `churches/router.py:72`, testy w `test_persons_search_authz.py`
- [x] Nie zwracać `email` w wynikach dopóki osoba nie zostanie wybrana? — **nie**; wyniki i tak są
  ograniczone do zborów w zasięgu wywołującego, a e-mail jest tym, po czym rozpoznaje się duplikat
  osoby przy dodawaniu do drugiego zboru

## SEC-5 — `POST /tenants` bez ograniczeń

Dziś: każdy zalogowany tworzy „zbór" i zostaje jego ownerem. Plan (governance, §5) rezerwuje tworzenie zborów dla biskupów i admina. Admin ma równoległy `POST /admin/tenants`.

- [x] Usunąć publiczny `POST /tenants` **albo** objąć go permissionem `church.create` — objęty
  `church.create` (admin/owner albo posiadacz uprawnienia); testy w `test_tenant_creation_authz.py`

## SEC-6 — widoczność nie odróżnia gościa od zalogowanego

`tenants/router.py` przekazuje `is_authenticated=False, has_pastoral_access=False` na sztywno. Skutki:

- `AclService.has_pastoral_access()` (`churches/acl_service.py`) to **martwy kod** — nikt go nie instancjonuje
- poziom widoczności `pastors` zachowuje się identycznie jak `hidden`
- zalogowany pastor nie widzi e-maili oznaczonych `authenticated` (domyślna wartość dla e-maila) na liście zborów

- [x] Czy `GET /congregations/detailed` ma mieć wariant dla zalogowanych (opcjonalny token)? —
  **tak, opcjonalny token na tym samym endpoincie**, bez osobnej ścieżki: jeden URL, treść zależna
  od tego, kto pyta
- [x] Podpiąć `AclService` do serializacji karty zboru
- [x] Test: gość vs zalogowany vs pastor widzą różne zestawy pól — `test_public_congregations_detailed.py`

## Powiązane (nie blokujące)

- **P-6:** publiczna lista filtruje po `address.status`, plan mówi `churches.visibility` →
  [#008](./2026-07-09--008--visibility-layer.md), zadania T10–T11 (backfill **przed** przełączeniem filtra)
- **Q-10:** macierz testów (rola × akcja × w/poza zasięgiem) — częściowo pokryta przez `tests/integration/congregations/test_congregations_authz.py`;
  pełna macierz w [acl-architecture.md §11](../plans/2026-07-25--acl-architecture.md), zadanie T7

## Zamknięcie (2026-07-25)

SEC-4, SEC-5 i SEC-6 zamknięte commitem `8b2f32f`. Dalsze hardenowanie autoryzacji (przejście
z członkostwa na `PermissionService`) prowadzi [#007](./2026-07-09--007--acl-roles-permissions.md).
