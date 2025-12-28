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
- Zobacz: `docs/features/FEATURE-XXX-contact-persons-public-flag.md` (do utworzenia)

---

**Ostatnia aktualizacja:** 2025-01-XX
