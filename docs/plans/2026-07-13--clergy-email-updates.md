# Aktualizacje danych zboru przez e-mail od duchownych — plan

**Status:** `verification needed`
**Created:** 2026-07-13

## Status update (2026-07-13)

Zaimplementowano fazy 1-3, każda zweryfikowana (black/mypy/pytest, migracja
uruchomiona realnie na lokalnym Postgresie 16):

- **Faza 1**: `EmailImportSettings`, migracja `068_email_import_tables.py`
  (`email_import_messages`, `congregation_change_log`, `last_updated_*`).
- **Faza 2**: `SenderResolver` (`app/modules/congregations/sender_resolver.py`)
  — autoryzacja nadawcy po e-mailu przez hierarchię church/region/community,
  8 testów jednostkowych. Przy okazji wydzielono `tenant_matching.py` ze
  wspólną logiką fuzzy-matchu.
- **Naprawiono po drodze**: kolizję numeracji migracji `066` (dwa niezależne
  PR-y użyły tego samego numeru, blokując `db migrate` na 067+) —
  przenumerowano `google_contacts_connections` na `069`.
- **Faza 3**: `imap_client.py` (stdlib `imaplib`/`email`, parsowanie
  SPF/DKIM/DMARC z `Authentication-Results`, ekstrakcja treści plain/html) +
  `email_import_service.py` (`EmailImportService.poll_and_process`) + CLI
  `python -m cli mail poll-inbox`. Kolejka jest zasilana (fetch → resolve →
  ekstrakcja AI z podpowiedzią kontekstową dla nadawcy z jednym własnym
  zborem → zapis do `email_import_messages` ze statusem `pending`) — **bez
  auto-zapisu**, to dopiero Faza 4.

- **Faza 4**: `OpenRouterProvider.verify_extraction` (osobny call AI: trust_score
  + uzasadnienie, kontekst = tożsamość nadawcy + diff pól — nigdy nie wpływa
  na wartości z ekstrakcji). Brama w `EmailImportService._resolve_and_maybe_apply`:
  najpierw tanie sprawdzenia strukturalne (SPF/DKIM/DMARC pass, a przy zmianie
  pól kontaktowych — czy dopasowany kontakt należy do samego nadawcy), dopiero
  potem (jeśli przeszły) wywołanie AI i porównanie z progiem
  `EMAIL_IMPORT_TRUST_THRESHOLD`. Zapis (`apply_fields`) następuje **przed**
  zapisaniem wiersza w `email_import_messages`, żeby błąd w trakcie zapisu nie
  zostawiał "widma" pomijanego przy dedupie. Każda auto-aplikowana zmiana ma
  wpis w `congregation_change_log` (`source=email_auto`), `last_updated_*` na
  adresie zboru i best-effort mail do admina (nowy szablon
  `email_import_auto_applied.html`). Przy okazji: wydzielono `field_diff.py`
  (współdzielone porównanie starych/nowych wartości) i upubliczniono
  `CongregationImportService.apply_fields` — używane teraz przez dwa serwisy.
  9 testów (auto-apply, niski trust_score, SPF fail, brak zmian).

- **Faza 5** (backend): `GET /admin/congregations/import/inbox`,
  `POST .../inbox/{id}/approve` (reużywa `apply_fields`, loguje
  `source=email_reviewed`), `POST .../inbox/{id}/reject`. Nowy
  `GET /congregations/{tenant_id}/change-log` — dostęp: admin, klasyczny
  członek tenanta LUB `AclService.has_pastoral_access` (pokrywa biskupa bez
  bezpośredniego członkostwa). 9 nowych testów integracyjnych.
- **Fazy 6-7** (frontend): `EmailImportInboxSection.vue` (nowa sekcja na
  `AdminCongregationImportPage.vue` — kolejka z tym samym UI diffu co paste-import,
  Zatwierdź/Odrzuć); `ChangeHistorySection.vue` (nowa sekcja na
  `EditCongregationPage.vue`, cicho znika przy 403 zamiast pokazywać błąd) +
  linijka „Ostatnia zmiana danych" nad formularzem (`last_updated_at/label`
  dodane do `AddressResponse`). `pnpm type-check`/`lint`/`build-only`/`test:run`
  (69) czyste.

Pozostało: Faza 8 (weryfikacja end-to-end z prawdziwym providerem AI i
prawdziwą skrzynką IMAP — nie do zrobienia w tym środowisku, brak
zewnętrznego dostępu sieciowego do IMAP/OpenRouter z prawdziwymi
danymi uwierzytelniającymi).

## Cel

Dedykowana skrzynka e-mail (np. `aktualizacje@zbory-chwz.pl`), na którą pastorzy,
biskupi i diakoni mogą wysłać wiadomość z aktualizacją danych swojego zboru
(adres, osoba kontaktowa, telefon, e-mail). Treść jest parsowana przez AI i:

1. przy wysokiej pewności (weryfikacja nadawcy + zgodność treści) — zapisywana
   **automatycznie**,
2. w pozostałych przypadkach — trafia do kolejki ręcznej weryfikacji admina
   (rozszerzenie istniejącego ekranu importu).

Każda zmiana — automatyczna czy ręczna — zostaje w historii widocznej na
profilu zboru, z informacją kto ją wprowadził.

## Ustalenia (z dyskusji 2026-07-13)

1. Odbiór poczty: **IMAP polling** dedykowanej skrzynki (nie webhook od
   zewnętrznego dostawcy — brak zmian MX/DNS, spójne z resztą backendu, które
   jest self-hosted). Cykliczne uruchamianie przez CLI (`python -m cli mail
   poll-inbox`) z crona, analogicznie do istniejących komend w `backend/cli/`.
2. Weryfikacja nadawcy — **dwuwarstwowa**:
   - dopasowanie `From:` do istniejącego kontaktu (nie fuzzy — dokładny e-mail),
   - anty-spoofing przez nagłówek `Authentication-Results` (SPF/DKIM/DMARC
     `pass` wymagany do jakiejkolwiek autoryzacji).
3. Uprawnienia hierarchiczne — biskup regionalny/naczelny może aktualizować
   wiele zborów:
   - brak miasta/nazwy zboru w treści → aktualizuje **swój** zbór (jedyny
     assignment nadawcy ze scope_type `church`; więcej niż jeden → do ręcznej
     kolejki),
   - podane miasto/nazwa → dopasowanie przez istniejący fuzzy-matcher, potem
     weryfikacja, czy nadawca ma dostęp do wskazanego zboru (bezpośrednio,
     przez region, przez wspólnotę).
4. Auto-zapis **tylko** przy spełnieniu wszystkich warunków bramki (SPF/DKIM/DMARC
   pass + autoryzowany zbór + `match_type == "matched"`, nigdy dla nowego zboru +
   wynik drugiego wywołania AI ≥ próg). Próg konfigurowalny: wartość domyślna w
   `AISettings`/`EmailImportSettings` (`backend/app/core/config.py`), nadpisywalna
   przez zmienną środowiskową — wzorzec identyczny jak istniejące `Field(default=...,
   validation_alias="ENV_VAR")`.
5. Bez funkcji "Cofnij" — pełny audit log + widoczna historia zmian
   wystarczają.
6. Historia zmian per zbór, widoczna w UI dla: adminów (wszystkie zbory) oraz
   zalogowanych pastorów/biskupów **tego konkretnego zboru** (i zborów objętych
   ich zasięgiem region/wspólnota). Dodatkowo kolumny `last_updated_*` na
   rekordach adresu/kontaktu do szybkiego wyświetlenia bez joina do logu.

## Kontekst techniczny (już w repo)

- **Pipeline ekstrakcji AI już istnieje** i jest reużywalny 1:1:
  `backend/app/modules/congregations/import_service.py`
  (`CongregationImportService.analyze/apply`) + `backend/app/modules/ai/provider.py`
  (`OpenRouterProvider.extract_congregations`, structured output przez OpenRouter
  `response_format: json_schema`). Endpointy `/admin/congregations/import/analyze`
  i `/apply` są dziś **bezstanowe** — nic nie jest zapisywane między krokami, więc
  dla maili (asynchroniczny wpływ danych) potrzebna jest nowa, trwała kolejka.
  Zob. [2026-07-11--congregation-address-text-import.md](2026-07-11--congregation-address-text-import.md).
- **Model kontaktów**: `PersonDB` (`backend/app/modules/churches/db_models.py`) ma
  `email` i opcjonalny `user_id` (konto platformowe — **tworzone tylko opcjonalnie**,
  `ServiceAssignmentCreateRequest.createAccount`, zob.
  `repositories.py::_maybe_create_user_and_acl`). Rola (pastor/biskup/diakon) i
  zasięg to `ServiceAssignmentDB.scope_type/scope_id` (`"church"` → tenant_id,
  potencjalnie `"region"`/`"community"` — patrz niżej).
- **Istniejący, gotowy do reużycia system ACL z dokładnie tą samą logiką
  hierarchii**: `backend/app/modules/churches/acl_service.py::AclService
  .has_pastoral_access(user_id, church_id)` sprawdza `UserRoleAssignmentDB`
  (scope `church`/`region`/`community`, złączone przez `ChurchDB.region_id` /
  `community_id`) dla ról z `PASTORAL_ROLE_NAMES` (`acl_seed.py`). To dokładny
  wzorzec do wykorzystania dla **UI historii zmian** (nadawca/przeglądający jest
  zalogowanym userem).
  - `UserRoleAssignmentDB.source_assignment_id` pokazuje, że role ACL bywają
    tworzone na bazie `ServiceAssignmentDB` — ale tylko gdy powstało konto
    (`createAccount=True`). **Wielu duchownych nie będzie miało konta**, więc do
    autoryzacji nadawcy maila potrzebny jest analogiczny resolver oparty
    bezpośrednio o `PersonDB.email` + `ServiceAssignmentDB` (bez wymogu loginu),
    a nie o `AclService`.
- **Adres zboru**: `CongregationAddressDB` (`backend/app/modules/congregations/db_models.py`)
  — `tenant_id`, `church_id`, `street/city/postal_code/province/country`.
- **Brak dziś**: jakiejkolwiek obsługi poczty przychodzącej (jest tylko wysyłka:
  `backend/app/core/email/{adapter,smtp_adapter,file_adapter,retry_smtp_adapter,
  audit_adapter}.py`), schedulera/crona w apce (IMAP polling będzie wywoływany
  zewnętrznym cronem systemowym, jak inne komendy CLI), oraz jakiegokolwiek
  śledzenia "kto ostatnio edytował" dane zboru.
- Precedens ryzyka automatycznego dopasowania bez weryfikacji człowieka:
  [#018](../issues/2026-07-10--018--congregation-address-data-quality.md) — uzasadnia
  konserwatywne domyślne ustawienia bramki auto-apply (wysoki próg, zero auto
  dla nowych zborów).

## Architektura

### 1. Konfiguracja

`backend/app/core/config.py` — nowa sekcja `EmailImportSettings`:
- `enabled: bool` (`EMAIL_IMPORT_ENABLED`)
- `imap_host/port/user/password/mailbox` (`EMAIL_IMPORT_IMAP_*`)
- `imap_use_ssl: bool`
- `trust_auto_apply_threshold: float = 0.9` (`EMAIL_IMPORT_TRUST_THRESHOLD`)

`.env.example` — nowa sekcja z powyższymi zmiennymi (pusty `IMAP_PASSWORD`
domyślnie, jak `OPENROUTER_API_KEY`).

### 2. Model danych (nowe migracje)

- **`email_import_messages`** (kolejka): `id`, `message_id` (RFC822 Message-ID,
  do deduplikacji przy ponownym pollingu), `raw_from`, `sender_person_id`
  (nullable FK `persons.id`), `resolved_tenant_id` (nullable FK), `resolution`
  (`own_church` / `matched_by_name` / `unauthorized` / `unknown_sender` /
  `ambiguous`), `auth_spf/dkim/dmarc` (string wynik z `Authentication-Results`),
  `extraction_json`, `verification_score` (float, nullable), `verification_reasoning`
  (text, nullable), `status` (`pending` / `auto_applied` / `approved` / `rejected`),
  `reviewed_by_user_id` (nullable), `reviewed_at`, `created_at`.
- **`congregation_change_log`**: `id`, `tenant_id`, `section` (`address`/`contact`),
  `field`, `old_value`, `new_value`, `source` (`admin_manual`/`import_paste`/
  `email_auto`/`email_reviewed`), `actor_label` (tekst do wyświetlenia),
  `actor_user_id` (nullable), `actor_person_id` (nullable), `email_import_message_id`
  (nullable FK), `created_at`.
- Kolumny `last_updated_at`/`last_updated_label` na `CongregationAddressDB` i
  (przez wspólną funkcję zapisu) na kontakcie — wypełniane przy każdym zapisie z
  `import_service.py`, żeby profil zboru nie musiał joinować do pełnego logu.

### 3. Resolver autoryzacji nadawcy (nowy, bez wymogu konta)

Nowy moduł, np. `backend/app/modules/congregations/email_import/sender_resolver.py`:

- `resolve_sender(email: str) -> PersonDB | None` — dokładne dopasowanie po
  `PersonDB.email` (case-insensitive).
- `resolve_target_tenant(person, extracted_name_or_city) -> tenant_id | None` —
  brak nazwy/miasta → jedyny assignment `scope_type="church"` osoby (więcej niż
  jeden → `None`/ambiguous); podana nazwa/miasto → istniejący
  `_match_tenant` z `import_service.py`.
- `is_authorized(person, target_tenant_id) -> bool` — analogiczna do
  `AclService.has_pastoral_access`, ale po `ServiceAssignmentDB` osoby zamiast
  `UserRoleAssignmentDB`: `scope_type="church"` wprost, `"region"`/`"community"`
  przez `ChurchDB.region_id`/`community_id` zbioru docelowego.
- Wynik (`resolution`) zapisywany w `email_import_messages` do audytu i debugowania.

### 4. Rozszerzenie AI — drugi call weryfikacyjny

`backend/app/modules/ai/provider.py` — nowa metoda
`verify_extraction(raw_text, extraction, sender_context, current_values) ->
VerificationResult` (`trust_score: float`, `reasoning: str`), osobny
`response_format: json_schema`. `sender_context` zawiera rozpoznaną tożsamość
(imię, rola, zbór) — model ocenia spójność (np. podpis w mailu vs. rozpoznany
nadawca), a nie tylko wierność ekstrakcji.

### 5. IMAP polling

Nowy moduł `backend/app/modules/congregations/email_import/imap_client.py`
(biblioteka standardowa `imaplib` + `email` — bez nowej zależności) +
`service.py` (`EmailImportService.poll_and_process()`):

1. Pobiera nieprzetworzone wiadomości (po `message_id`, IMAP flag `\Seen`/UID).
2. Parsuje `Authentication-Results`, `From`, treść (plain text; HTML → fallback
   strip tagów).
3. `sender_resolver.resolve_sender` → `resolve_target_tenant` → `is_authorized`.
4. `OpenRouterProvider.extract_congregations` (reużycie) →
   `CongregationImportService._build_proposal`-owy diff względem
   `resolved_tenant_id`.
5. `verify_extraction` (etap 2).
6. Bramka: SPF/DKIM/DMARC pass ∧ autoryzowany ∧ `match_type=="matched"` ∧
   `trust_score ≥ trust_auto_apply_threshold` ∧ zmiana dotyczy tylko rekordu
   nadawcy → `CongregationImportService._apply_fields` (reużycie) +
   `status="auto_applied"` + wpis w `congregation_change_log`
   (`source="email_auto"`, `actor_person_id`).
7. W przeciwnym razie → `status="pending"`, bez zapisu do danych zboru.

`backend/cli/commands/mail.py` — `mail_app` (Typer), komenda `poll-inbox`,
zarejestrowana w `cli/main.py` obok `users`/`tenants`/`db`. Uruchamiana cronem
systemowym (dokumentacja w README backendu, nie w apce — brak schedulera).

### 6. Backend — kolejka ręcznej weryfikacji (admin)

Rozszerzenie `backend/app/modules/congregations/import_router.py` (lub nowy
router `email_import_router.py`) o:
- `GET /admin/congregations/import/inbox` — lista `email_import_messages` ze
  statusem `pending` (+ szczegóły do przeglądu: diff, `verification_reasoning`,
  wynik resolvera).
- `POST /admin/congregations/import/inbox/{id}/approve` — jak istniejący
  `/apply`, plus `source="email_reviewed"` w logu, `reviewed_by_user_id`.
- `POST /admin/congregations/import/inbox/{id}/reject`.

### 7. Frontend — kolejka mailowa

Rozszerzenie `AdminCongregationImportPage.vue` (lub nowa zakładka) o listę
oczekujących wiadomości z tym samym komponentem przeglądu diff co dziś (paste
flow), doładowanym o: nadawcę, wynik autoryzacji, `verification_score`/
`reasoning` jako kontekst dla admina.

### 8. Frontend — historia zmian na profilu zboru

- Nowy komponent (np. `ChangeHistorySection.vue`) na `EditCongregationPage.vue`
  (i odpowiedniku admina), lista z `congregation_change_log` per tenant.
- Widoczność: admin — zawsze; zalogowany user — tylko gdy
  `AclService.has_pastoral_access(user.id, church_id)` (reużycie istniejącego
  serwisu, żadnej nowej logiki uprawnień po stronie backendu poza jednym
  guardem na nowym endpoincie `GET /congregations/{id}/change-log`).
- `last_updated_at/label` jako skrócony badge widoczny bez wchodzenia w pełną
  historię (tylko dla uprawnionych — jak wyżej).

### 9. i18n

Nowe klucze w `src/modules/admin/i18n/locales/{en,pl}.json` i
`src/modules/congregations/i18n/locales/{en,pl}.json` (historia zmian, statusy
kolejki, etykiety źródła zmiany).

## Bezpieczeństwo / jakość danych

- SPF/DKIM/DMARC `pass` wymagany do jakiejkolwiek autoryzacji — brak/`fail` ⇒
  zawsze ręczna kolejka, niezależnie od pewności AI.
- Dopasowanie nadawcy **dokładne** po e-mailu, nigdy fuzzy.
- `match_type == "new"` (nowy zbór) — **nigdy** auto-apply, zawsze ręczna kolejka
  (spójne z zasadą "zero auto-zapisu dla nowych rekordów" z importu ręcznego).
- Auto-apply ogranicza się do rekordu nadawcy (adres jego zboru + jego własny
  kontakt) — nie pozwala edytować danych innej osoby w tym samym zborze bez
  przeglądu.
- Próg zaufania konfigurowalny, domyślnie konserwatywny (0.9) — do
  doprecyzowania w Fazie 8 na realnych danych.
- Pełny audit log (`email_import_messages` + `congregation_change_log`)
  niezależnie od ścieżki (auto i ręcznej), z powiadomieniem admina mailem przy
  każdym auto-apply (reużycie `core/email/service.py`).

## Fazy

| Faza | Zakres |
|------|--------|
| 0 | Ten dokument |
| 1 | Backend: `EmailImportSettings` + migracje (`email_import_messages`, `congregation_change_log`, `last_updated_*`) |
| 2 | Backend: sender resolver (`PersonDB`/`ServiceAssignmentDB`, hierarchia church/region/community) + parsowanie SPF/DKIM/DMARC |
| 3 | Backend: IMAP polling (`imap_client.py`, `service.py`) + CLI `mail poll-inbox`, integracja z `CongregationImportService.analyze` |
| 4 | Backend: drugi call AI (`verify_extraction`) + bramka auto-apply + zapis do `congregation_change_log` + powiadomienie mailowe admina |
| 5 | Backend: endpointy kolejki ręcznej (`GET /inbox`, `approve`, `reject`) + endpoint historii zmian (`GET /congregations/{id}/change-log`, gated `AclService`) |
| 6 | Frontend: kolejka mailowa w `AdminCongregationImportPage.vue` |
| 7 | Frontend: zakładka "Historia zmian" na `EditCongregationPage.vue` + badge `last_updated_*` |
| 8 | Weryfikacja end-to-end (skrzynka testowa, mock IMAP w testach, prawdziwy provider ręcznie), doprecyzowanie progu zaufania, `.env.example`, testy integracyjne |

## Weryfikacja

1. `docker exec zbory-chwz-app python -m pytest tests/ -v` — nowe testy
   jednostkowe (`sender_resolver`, bramka auto-apply, parsowanie
   `Authentication-Results`) i integracyjne (kolejka, endpointy).
2. `cd backend && python -m black . && python -m mypy .`
3. `pnpm type-check && pnpm lint`
4. Manualnie: wysłać testowy e-mail z aktualizacją danych na skrzynkę dev,
   uruchomić `python -m cli mail poll-inbox`, sprawdzić: (a) wysoka pewność +
   autoryzowany nadawca → auto-zapis + wpis w historii, (b) nieznany nadawca /
   nieautoryzowany zbór / niska pewność → pozycja w kolejce ręcznej, (c) historia
   zmian widoczna dla admina i dla zalogowanego pastora danego zboru, niewidoczna
   dla innych zalogowanych userów.

## Powiązane

- [2026-07-11--congregation-address-text-import.md](2026-07-11--congregation-address-text-import.md) — bazowy pipeline ekstrakcji/dopasowania/diff, reużywany 1:1.
- [2026-07-09--church-platform.md](2026-07-09--church-platform.md) i [2026-07-09--organization-and-acl.md](2026-07-09--organization-and-acl.md) — model ACL (`church`/`region`/`community`) reużywany przez sender resolver i gating historii.
- [#018](../issues/2026-07-10--018--congregation-address-data-quality.md) — precedens ryzyka błędnego auto-dopasowania, uzasadnia konserwatywną bramkę auto-apply.
