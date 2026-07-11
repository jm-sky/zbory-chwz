# Import adresów zborów z wklejonego tekstu (AI-assisted) — plan

**Status:** `verification needed`
**Created:** 2026-07-11

## Status update (2026-07-11)

Zaimplementowano fazy 1-3 (backend: moduł `app/modules/ai`, endpointy
`/admin/congregations/import/analyze` i `/apply`; frontend:
`AdminCongregationImportPage.vue`). Zweryfikowano automatycznie:
`pytest` (nowe testy + cały pakiet `tests/integration/congregations/`),
`black`, `mypy`, `pnpm type-check`, `pnpm lint`, `pnpm build`. **Brak
ręcznej weryfikacji end-to-end w przeglądarce z prawdziwym kluczem
OpenRouter** (środowisko implementacyjne nie miało Dockera/Postgresa) —
zalecane przed oznaczeniem jako `done`: uruchomić `docker compose -f
backend/docker-compose.dev.yml up` + `pnpm dev`, ustawić
`OPENROUTER_API_KEY`, i przejść scenariusz z sekcji Weryfikacja poniżej.

## Cel

Strona (dla admina/ownera), gdzie można wkleić wolny tekst z adresami kilku
zborów naraz (np. notatka z rozmowy telefonicznej albo e-maila), a system:

1. rozpoznaje poszczególne zbory w tekście i wyciąga strukturalne dane
   (adres + osoba kontaktowa) — przy wsparciu AI (OpenRouter),
2. dopasowuje je do istniejących rekordów w bazie po nazwie (fuzzy match),
3. pokazuje ekran przeglądu (stara wartość → nowa, pole po polu) do ręcznej
   akceptacji,
4. po zatwierdzeniu zapisuje zmiany — aktualizuje istniejące zbory albo
   tworzy nowe, jeśli dopasowania nie znaleziono.

## Ustalenia (2026-07-11)

1. Parsowanie tekstu: **AI (OpenRouter) od razu**, z structured output
   (`response_format: json_schema`), a nie regex na wolnym tekście odpowiedzi
   czatu (to ostatnie jest wzorcem z gear-stacka, ale kruchym — tu robimy to
   solidniej).
2. Zakres pól mapowania: **adres + osoba kontaktowa** (nie tylko adres).
3. Brak dopasowania nazwy do istniejącego zboru: **update istniejących +
   tworzenie nowych zborów**, gdy dopasowania nie znaleziono (analogicznie do
   przepływu z [google-contacts-sync.md](2026-07-10--google-contacts-sync.md)).
4. **Zero auto-zapisu** — każda zmiana (i każde dopasowanie) wymaga jawnej
   akceptacji admina na ekranie przeglądu, z możliwością ręcznej korekty
   dopasowania i wartości pól przed zapisem.

## Kontekst techniczny (już w repo)

- Model danych zboru jest rozproszony: nazwa w `tenants`/`churches`, adres w
  `congregation_addresses` (`street`, `city`, `postal_code`, `province`,
  `country` — **bez współrzędnych geograficznych**, geokodowanie poza
  zakresem), kontakt w `congregation_contact_persons` (`name`, `title`,
  `email`, `phone`). Zob. `backend/app/modules/congregations/db_models.py`.
- **Nie istnieje dziś żaden działający moduł AI** w tym repo, mimo że
  `CLAUDE.md` go wymienia jako istniejący moduł — to placeholder (martwy
  import `app.modules.ai...` w `backend/cli/commands/test.py` wskazujący na
  nieistniejący pakiet). `openai>=1.0.0` jest już w `requirements.txt`, ale
  nieużywany.
- Siostrzany projekt **gear-stack** ma działającą integrację z OpenRouter
  (`backend/app/modules/ai/providers/openrouter.py`): `AsyncOpenAI` wskazany
  na `https://openrouter.ai/api/v1`. Structured output tam jest wyciągany
  regexem z bloku ```json``` w odpowiedzi czatu — tu robimy to przez natywny
  `response_format: json_schema` OpenRoutera zamiast kopiować ten fragment.
- Brak biblioteki do fuzzy-matchingu (frontend i backend) — potrzebny
  `rapidfuzz` po stronie backendu. Istniejący `slugify()`
  (`backend/app/modules/churches/slug_utils.py`) można użyć do normalizacji
  nazw przed porównaniem.
- Znany case [#018](../issues/2026-07-10--018--congregation-address-data-quality.md):
  automatyczne dopasowanie bez weryfikacji człowieka już raz wpisało błędny
  adres do bazy (`ZBÓR W ŚWIEBODZINIE` dostał adres z Rzuchowej ze scrape'a).
  To bezpośrednio uzasadnia wymóg ręcznej weryfikacji dopasowania w UI.
- [google-contacts-sync.md](2026-07-10--google-contacts-sync.md) to bardzo
  zbliżony koncepcyjnie, ale niezaimplementowany plan (import → fuzzy-match →
  ekran mapowania/podglądu → potwierdzenie) — dobry punkt odniesienia dla UX,
  ale nie blokuje tej funkcji (mniejszy zakres, brak zależności od OAuth
  Google).

## Architektura

### 1. Nowy, minimalny moduł AI (backend)

Nie kopiujemy całej infrastruktury gear-stacka (chat/history/cache/
szyfrowanie tokenu usera, wybór modelu per-user) — to funkcja tylko dla
admina/ownera, z systemowym kluczem, jednym przeznaczeniem.

- `backend/app/core/config.py` — `AISettings`: `enabled`,
  `openrouter_api_key` (`OPENROUTER_API_KEY`), `openrouter_base_url`
  (default `https://openrouter.ai/api/v1`), `model` (`AI_MODEL`, np.
  `openai/gpt-4o-mini` — model musi wspierać `response_format: json_schema`
  na OpenRouterze).
- `backend/app/modules/ai/provider.py` — `AsyncOpenAI(api_key=..., base_url=...)`,
  metoda `extract_congregations(raw_text: str) -> list[ExtractedCongregation]`
  z `response_format={"type": "json_schema", "json_schema": {..., "strict": True}}`,
  parsowanie odpowiedzi przez Pydantic (bez regexa).
- `.env.example` — `AI_ENABLED`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `AI_MODEL`.
- `backend/requirements.txt` — dodać `rapidfuzz`.

### 2. Rozszerzenie modułu `congregations` (backend)

- **`POST /admin/congregations/import/analyze`** (`AdminOrOwnerUser`) —
  `{ raw_text: str }` →
  1. AI provider wyciąga listę zborów (nazwa, adres, kontakt) z tekstu.
  2. `rapidfuzz.process.extractOne` po znormalizowanych nazwach wszystkich
     tenantów → próg pewności (np. ≥80 = dopasowanie, poniżej = `unmatched`).
  3. Dla dopasowanych: diff pól względem aktualnego stanu (przez istniejące
     `CongregationRepository.get_address_by_tenant_id` /
     `get_contact_persons_by_tenant_id`).
  4. Dla niedopasowanych: `match_type: "new"`, wszystkie pola jako nowe.
  5. **Nic nie zapisuje** — zwraca propozycje z `confidence`, `match_type`,
     `tenant_id | null`, diff adresu i kontaktu.
- **`POST /admin/congregations/import/apply`** — propozycje *po edycji przez
  admina* (per-pole `apply: bool`, poprawione wartości, ew. ręcznie
  skorygowany `tenant_id` albo `action: "create_new"`):
  - Dopasowane + apply → `CongregationRepository.create_or_update_address(...)`
    + create/update contact person — reużycie metod już używanych przez
    istniejące endpointy (`PATCH /congregations/{id}/address` itd.), bez
    nowej logiki zapisu.
  - Nowe + apply → `TenantRepository.create_tenant(...)` +
    `provision_church_for_tenant(...)` (jak w
    `admin/router.py::create_tenant_admin`), potem adres/kontakt jak wyżej.
  - Walidacja `is_valid_province()` (`congregations/geo.py`) musi przejść
    przed zapisem — ta sama ścieżka co istniejący `update_address`.
  - Zwraca `{created, updated, skipped}`.
- Schematy w `backend/app/modules/congregations/schemas.py`:
  `ImportAnalyzeRequest`, `ImportProposal`, `ImportAnalyzeResponse`,
  `ImportApplyRequest`, `ImportApplyResponse`.
- Bez tabeli audytu importu w V1 (uproszczenie względem
  `google-contacts-sync.md`) — do rozważenia później.

### 3. Frontend

- `src/modules/admin/pages/AdminCongregationImportPage.vue`, trasa
  `/admin/congregations/import`, `meta: { requiresAdmin: true }`; link z
  `AdminCongregationsPage.vue` (obok istniejącego menu eksportu).
- `src/modules/admin/services/congregationImportApiService.ts` —
  `analyze(rawText)` / `apply(proposals)` przez współdzielony `apiClient`.
- `src/modules/admin/types/congregationImport.types.ts` — typy propozycji/diffów.
- Przepływ UI (dwuetapowy, bez auto-zapisu):
  1. `<Textarea>` + przycisk „Analizuj” (loading/error wzorem
     `useHandleError`/toast).
  2. Ekran przeglądu — karta na każdy wykryty zbór: nagłówek z wykrytą nazwą
     + badge dopasowania („Dopasowano do: X” / „Nowy zbór” / „Brak
     dopasowania — wybierz ręcznie”, z `confidence`) + `Select` do ręcznej
     korekty dopasowania; wiersz na pole (stara → nowa wartość, checkbox
     „zastosuj”, edytowalny input); przełącznik „pomiń ten zbór”.
  3. „Zastosuj zaznaczone zmiany” → `apply()` → toast z podsumowaniem →
     `queryClient.invalidateQueries({queryKey: ['congregations']})`.
- i18n: nowe klucze w `src/modules/admin/i18n/locales/{en,pl}.json`.

## Bezpieczeństwo / jakość danych

- Endpointy tylko dla `AdminOrOwnerUser`.
- Zero zapisu bez jawnego kliknięcia „Zastosuj”.
- Nowy zbór wymaga co najmniej `city` (`nullable=False` w
  `CongregationAddressDB`) — walidacja przed „Zastosuj”.
- Niskie `confidence` dopasowania wyraźnie oznaczone w UI.

## Fazy

| Faza | Zakres |
|------|--------|
| 0 | Ten dokument |
| 1 | Backend: moduł AI (config + provider) + endpoint `analyze` (ekstrakcja + fuzzy-match, bez zapisu) |
| 2 | Backend: endpoint `apply` (update/create) + testy integracyjne |
| 3 | Frontend: strona importu, ekran przeglądu, i18n |
| 4 | Weryfikacja end-to-end na danych seedowych, doprecyzowanie progu fuzzy-match |

## Weryfikacja

1. `docker exec zbory-chwz-app python -m pytest tests/integration/congregations/test_import_analyze.py tests/integration/congregations/test_import_apply.py -v`
   — z zamockowanym AI providerem, testy fuzzy-matchingu i zapisu (update/create/walidacja province).
2. `cd backend && python -m black . && python -m mypy .`
3. `pnpm type-check && pnpm lint`
4. Manualnie: wkleić notatkę z 2–3 zborami (jeden pasujący do danych
   seedowych, jeden nowy) na `/admin/congregations/import`, sprawdzić diff,
   zatwierdzić, zweryfikować w `EditCongregationPage.vue`.

## Powiązane

- [google-contacts-sync.md](2026-07-10--google-contacts-sync.md) — analogiczny
  wzorzec importu (mapowanie + podgląd), inny kanał danych źródłowych
- [#018](../issues/2026-07-10--018--congregation-address-data-quality.md) —
  precedens ryzyka błędnego auto-dopasowania adresu
