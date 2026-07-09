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

🔄 **Status:** Planowane

**Opis:**
Definiowanie grup organizacyjnych poza zborami, np. Prezydium Rady Naczelnej, Grupa Ewangelizacji, Służba Więzienna.

**Szczegóły:**
- Issue: [#014](issues/2026-07-09--014--people-groups.md)
- Plan: [people-groups.md](plans/2026-07-09--people-groups.md)

---

### Listy mailingowe

🔄 **Status:** Planowane (późniejsza faza)

**Opis:**
Listy mailingowe oparte o grupy ludzi i adresy `persons` — komunikacja wewnętrzna CHWZ.

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

**Ostatnia aktualizacja:** 2026-07-09
