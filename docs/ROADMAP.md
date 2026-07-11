# ROADMAP - Zbory CHWZ

Główny indeks roadmap projektu Zbory CHWZ.

## 📋 Struktura Roadmap

- **[ROADMAP_OFFLINE.md](./ROADMAP_OFFLINE.md)** - Funkcjonalności działające wyłącznie na localStorage (offline-first)
- **[ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md)** - Funkcjonalności wymagające backendu/DB/autoryzacji

## 🔄 Statusy

- ✅ **Zrealizowane** - Funkcjonalność jest w pełni zaimplementowana i działa
- 🚧 **W trakcie** - Funkcjonalność jest częściowo zaimplementowana
- 🔄 **Planowane** - Funkcjonalność jest zaplanowana do implementacji
- ❌ **Anulowane** - Funkcjonalność została anulowana

## 📝 Nowe funkcjonalności

### Ludzie i służby — jeden model, widoczność na karcie zboru

🚧 **Status:** W trakcie (MVP zaimplementowany)

**Opis:**
Bez osobnego modelu „osoba kontaktowa”. Wystarczy **służba** (`service_assignment` + `person`). Każda osoba w służbie ma przełącznik widoczności na publicznej karcie zboru; **telefon** i **e-mail** mają osobne przełączniki widoczności.

**Zrealizowane (2026-07-09):**
- Migracja `057` + pola `show_on_card`, `phone_public`, `email_public`
- UI: jedna sekcja „Ludzie i służby” z przełącznikami widoczności
- Backfill: `contact_persons` → `service_assignments` (idempotentny)
- Publiczna lista zborów korzysta z przypisań służby

**Pozostało:**
- Deprecate API `contact_persons` (endpointy legacy nadal istnieją)
- Pełna warstwa widoczności enum (#008) zamiast boolean MVP

**Szczegóły:**
- Issue: [#012](issues/2026-07-09--012--unify-services-remove-contact-persons.md)
- Plan: [church-assignment-visibility.md](plans/2026-07-09--church-assignment-visibility.md)
- Bug selecta służb: [#013](issues/2026-07-09--013--service-type-select-not-visible.md) ✅

---

### Grupy ludzi

🚧 **Status:** W trakcie (faza 1 zaimplementowana)

**Opis:**
Definiowanie grup organizacyjnych poza zborami, np. Prezydium Rady Naczelnej, Grupa Ewangelizacji, Służba Więzienna. Widoczność konfigurowalna per grupa, opiekun grupy zarządza członkami bez pełnych uprawnień admina, członkostwo nie nadaje uprawnień ACL.

**Zrealizowane (2026-07-10/11):**
- Migracja `062` + tabele `people_groups`, `people_group_memberships`
- API `/api/people-groups` (CRUD grup + członkostwa)
- UI: lista grup (`/groups`), szczegóły grupy, dodawanie/usuwanie członków
- Wyszukiwarka osób (autocomplete) w formularzu dodawania członka — ta sama, wspólna z edytorem zboru

**Pozostało:**
- UI do edycji roli istniejącego członka (backend `PATCH .../memberships/{id}` gotowy, frontend go nie używa)
- Publiczna, niezalogowana strona grupy o `visibility: public` (dziś każda grupa wymaga zalogowania)

**Szczegóły:**
- Issue: [#014](issues/2026-07-09--014--people-groups.md)
- Plan: [people-groups.md](plans/2026-07-09--people-groups.md)

---

### Eksport adresów e-mail + przeglądarka wszystkich osób

✅ **Status:** Zrealizowane (fazy 1–2)

**Opis:**
Narzędzie do budowania listy adresów e-mail (filtr: region + rola/służba + grupa ludzi) i kopiowania jej do schowka — do wklejenia w Gmail/Outlook. **Nie** wysyłka z poziomu aplikacji — MVP celowo bardzo okrojone względem pierwotnej koncepcji „list mailingowych” z kampaniami i dostawcą SMTP/ESP, którą odłożono bezterminowo. W tym samym module (druga zakładka) — przeglądarka wszystkich osób w zasięgu: podgląd z odznakami przynależności, edycja danych kontaktowych, scalanie duplikatów. Dostęp oparty o istniejący ACL (`user_role_assignments`): pastor/diakon widzi swój zbór, regional_bishop swój region, bishop swoją wspólnotę, admin/owner wszystko.

**Zrealizowane (2026-07-11):**
- API `/api/people-directory/filters` + `/export` (faza 1) oraz `/persons`, `/persons/{id}` (GET/PATCH), `/persons/merge` (faza 2) — `backend/app/modules/directory`, zasięg egzekwowany po stronie backendu
- UI: `/people-directory` — zakładka „Eksport adresów” (filtry, wyniki, ręczne dodawanie, kopiowanie w 2 formatach) i zakładka „Wszystkie osoby” (wyszukiwanie, lista z odznakami przynależności, dialog edycji, scalanie duplikatów z potwierdzeniem)
- 19 testów integracyjnych (9 + 10) + weryfikacja end-to-end w przeglądarce dla obu faz

**Pozostało (opcjonalnie, później):**
- Zapisane/nazwane filtry, wysyłka przez SMTP/ESP, usuwanie osób — nieplanowane, prawdopodobnie niepotrzebne

**Szczegóły:**
- Issue: [#015](issues/2026-07-09--015--mailing-lists.md)
- Plan: [mailing-lists.md](plans/2026-07-09--mailing-lists.md)

---

### Platforma zborów — hierarchia, ACL, publiczne URL

🔄 **Status:** Planowane

**Opis:**
Pełna platforma zarządzania zborami CHWZ: hierarchia organizacyjna (wspólnota → rejon → zbór → placówka), rozdzielone role i uprawnienia (ACL), warstwa widoczności oraz publiczne adresy `/kraj/miasto/slug-zboru`.

**Źródła koncepcyjne:**
- `docs/plans/2026-07-09--church-platform.md`
- `docs/plans/2026-07-09--organization-and-acl.md`

**Plan implementacji:**
- `docs/plans/2026-07-09--church-platform-implementation.md`

**Issues:** #006–#010 w `docs/issues/`

---

**Ostatnia aktualizacja:** 2026-07-11
