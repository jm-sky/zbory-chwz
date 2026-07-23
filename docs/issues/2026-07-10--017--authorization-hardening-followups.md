# Hardening autoryzacji — decyzje do podjęcia

**Status:** `todo`
**Created:** 2026-07-10
**Component:** `churches/router.py`, `tenants/router.py`, `churches/acl_service.py`
**Related:** [#007](./2026-07-09--007--acl-roles-permissions.md) · [#008](./2026-07-09--008--visibility-layer.md) · [review 2026-07-10](../reviews/2026-07-10--church-platform-review.md) (SEC-4, SEC-5, SEC-6)

## Kontekst

Review z 2026-07-10 zamknął krytyczne dziury (IDOR na `/congregations/*`, eskalacja do `bishop` przez `suggestedRole`, zapis międzyzborowy). Zostały trzy pozycje wymagające **decyzji produktowej**, nie samego kodu.

## SEC-4 — zakres `GET /churches/persons/search`

Dziś: dowolne zalogowane konto przeszukuje globalną bazę osób po imieniu, nazwisku i e-mailu. To scraper adresów wszystkich pastorów i diakonów CHWZ. Endpoint nie jest jeszcze używany przez UI.

**Do decyzji:** ograniczyć do admin/owner, czy do posiadaczy `services.manage` w jakimkolwiek zasięgu?

- [ ] Wybrać zakres i wdrożyć
- [ ] Nie zwracać `email` w wynikach dopóki osoba nie zostanie wybrana?

## SEC-5 — `POST /tenants` bez ograniczeń

Dziś: każdy zalogowany tworzy „zbór" i zostaje jego ownerem. Plan (governance, §5) rezerwuje tworzenie zborów dla biskupów i admina. Admin ma równoległy `POST /admin/tenants`.

- [ ] Usunąć publiczny `POST /tenants` **albo** objąć go permissionem `church.create`

## SEC-6 — widoczność nie odróżnia gościa od zalogowanego

`tenants/router.py` przekazuje `is_authenticated=False, has_pastoral_access=False` na sztywno. Skutki:

- `AclService.has_pastoral_access()` (`churches/acl_service.py`) to **martwy kod** — nikt go nie instancjonuje
- poziom widoczności `pastors` zachowuje się identycznie jak `hidden`
- zalogowany pastor nie widzi e-maili oznaczonych `authenticated` (domyślna wartość dla e-maila) na liście zborów

- [ ] Czy `GET /congregations/detailed` ma mieć wariant dla zalogowanych (opcjonalny token)?
- [ ] Podpiąć `AclService` do serializacji karty zboru
- [ ] Test: gość vs zalogowany vs pastor widzą różne zestawy pól

## Powiązane (nie blokujące)

- **P-6:** publiczna lista filtruje po `address.status`, plan mówi `churches.visibility`
- **Q-10:** macierz testów (rola × akcja × w/poza zasięgiem) — częściowo pokryta przez `tests/integration/congregations/test_congregations_authz.py`
