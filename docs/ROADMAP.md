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

### Kontakt osoby - flaga publiczna

🔄 **Status:** Planowane

**Opis:**
Dodanie flagi `public` dla osób kontaktowych w zborach. Osoby kontaktowe domyślnie są publiczne i widoczne dla wszystkich użytkowników (również niezalogowanych). Odznaczenie flagi `public` powoduje ukrycie osoby i widoczność tylko dla zalogowanych użytkowników.

**Przykład użycia:**
- Pastor może być oznaczony jako publiczny (widoczny dla wszystkich)
- Diakon może być oznaczony jako niepubliczny (widoczny tylko dla zalogowanych)

**Wymagania:**
- Backend: Dodanie pola `is_public` (domyślnie `true`) do tabeli `contact_persons`
- Frontend: Dodanie checkboxa w formularzu edycji osoby kontaktowej
- Filtrowanie: W publicznym widoku zboru pokazywać tylko osoby z `is_public = true`
- Widok dla zalogowanych: Pokazywać wszystkie osoby (publiczne i niepubliczne)

**Szczegóły implementacji:**
- Zobacz: `docs/plans/2026-07-09--church-platform-implementation.md` (Phase 3 — visibility layer, issue #008)

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
