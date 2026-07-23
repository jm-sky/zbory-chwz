# Gear Stack - Lista Funkcjonalności

## 📋 O Projekcie

Gear Stack to zaawansowana aplikacja webowa do zarządzania ekwipunkiem survivalowym, plecakami bug-out oraz sprzętem outdoorowym. Aplikacja działa w architekturze full-stack z obsługą wielu użytkowników, synchronizacją w chmurze i zaawansowanymi funkcjami organizacyjnymi.

**Wersja:** 2.43.0

---

## 🔐 Bezpieczeństwo i Uwierzytelnianie

### Zarządzanie Użytkownikami
- ✅ **Rejestracja i logowanie** - klasyczna autentykacja email/hasło z bezpiecznym hashowaniem (bcrypt)
- ✅ **Weryfikacja email** - potwierdzanie adresu email dla zwiększenia bezpieczeństwa
- ✅ **Zarządzanie hasłem** - resetowanie zapomnianego hasła, zmiana hasła dla zalogowanych
- ✅ **Zarządzanie sesjami** - tokeny JWT z automatycznym odświeżaniem, bezpieczne wylogowanie
- ✅ **Usuwanie konta** - zgodne z RODO, z potwierdzeniem (soft delete)

### OAuth 2.0 - Logowanie przez Social Media
- ✅ **Google OAuth** - logowanie przez konto Google
- 🔄 **GitHub OAuth** - planowane wsparcie dla GitHub
- ✅ **Automatyczne avatary** - zdjęcia profilowe z dostawców OAuth
- ✅ **Ochrona CSRF** - zabezpieczenie przez parametr state
- ✅ **Zarządzanie połączeniami OAuth** - przeglądanie i usuwanie połączonych kont OAuth w ustawieniach

### Uwierzytelnianie Dwuskładnikowe (2FA)
- ✅ **TOTP (Time-based OTP)** - wsparcie dla aplikacji typu Google Authenticator, Authy
- ✅ **WebAuthn** - wsparcie dla passkeys i kluczy sprzętowych (YubiKey, itp.)
- ✅ **Kody zapasowe** - na wypadek utraty dostępu do urządzenia 2FA
- ✅ **Zarządzanie metodami 2FA** - dodawanie, usuwanie, wyświetlanie statusu bezpieczeństwa

### Dodatkowe Zabezpieczenia
- ✅ **Rate Limiting** - ochrona przed atakami brute-force
- ✅ **reCAPTCHA v3** - niewidoczna ochrona przed botami (score-based)
- ✅ **CORS Configuration** - bezpieczne zapytania cross-origin
- ✅ **Ochrona przed SQL Injection** - parametryzowane zapytania przez SQLAlchemy
- ✅ **Ochrona przed XSS** - walidacja i sanityzacja danych wejściowych
- ✅ **Token Blacklist Service** - unieważnianie tokenów JWT przy wylogowaniu (Redis)
- ✅ **WebAuthn Challenge Storage** - bezpieczne przechowywanie wyzwań WebAuthn w Redis
- ✅ **Redis Infrastructure** - infrastruktura Redis dla token blacklist i challenge storage

---

## 🎒 Zarządzanie Ekwipunkiem

### System Kontenerów
- ✅ **Wiele typów kontenerów** - plecaki bug-out, zestawy EDC, get-home bags, apteczki, sprzęt kempingowy, własne typy
- ✅ **Hierarchiczna organizacja** - kontenery mogą zawierać inne kontenery (zagnieżdżone plecaki, saszetki)
- ✅ **Wizualne rozróżnienie** - przypisanie kolorów do kontenerów (10+ kolorów)
- ✅ **Metadane kontenerów** - typ, opis, waga podstawowa, kodowanie kolorami
- ✅ **Detekcja cykli** - zapobiega cyklicznym odwołaniom w zagnieżdżonych kontenerach
- ✅ **Klonowanie kontenerów** - duplikowanie kontenerów ze wszystkimi przedmiotami i zagnieżdżonymi kontenerami
- ✅ **Edycja inline nazwy** - szybka edycja nazwy kontenera bezpośrednio na stronie szczegółów kontenera
- ✅ **Kolejność przedmiotów** - ręczne ustawianie kolejności przedmiotów w kontenerze z potwierdzeniem zapisu

### Zarządzanie Przedmiotami
- ✅ **Bogate dane przedmiotów:**
  - Podstawowe: nazwa, ilość, waga (z wyborem jednostki: g, kg, oz, lb)
  - Organizacja: kategoria, priorytet, status (posiadane/brakujące/do kupienia)
  - Metadane: marka, notatki, data ważności, okres przydatności (shelf life)
  - Zaawansowane: flaga materiałów zużywalnych, flaga noszenia, własne kategorie
- ✅ **Inteligentna kategoryzacja** - automatyczne rozpoznawanie kategorii na podstawie nazwy przedmiotu
- ✅ **Śledzenie statusu** - oznaczanie jako posiadane, brakujące lub do kupienia
- ✅ **Poziomy priorytetu** - niski, średni, wysoki, krytyczny
- ✅ **Śledzenie daty ważności** - monitorowanie materiałów zużywalnych
- ✅ **Okres przydatności (Shelf Life)** - definiowanie okresu przydatności przedmiotów przed zakupem (dni/miesiące/lata), automatyczne obliczanie daty ważności
- ✅ **Dodawanie istniejących przedmiotów** - dodawanie przedmiotów z innych kontenerów przez selektor katalogu
- ✅ **Rozpoznawanie parametrów** - automatyczne wykrywanie marki i koloru z nazw przedmiotów
- ✅ **Zarządzanie markami** - własne marki z kolorami, zarządzanie w ustawieniach, integracja z formularzami i rozpoznawaniem parametrów
- ✅ **Wsparcie dla walut** - ceny w różnych walutach (PLN, EUR, USD, GBP, JPY, CHF, CAD, AUD), domyślna waluta użytkownika z auto-detekcją, formatowanie cen, wyświetlanie w tabelach i statystykach
- ✅ **Edycja inline nazwy** - szybka edycja nazwy przedmiotu bezpośrednio na stronie szczegółów przedmiotu
- ✅ **Przenoszenie przedmiotów między kontenerami** - możliwość przenoszenia przedmiotów do innych kontenerów z zachowaniem wszystkich danych
- ✅ **Linkowanie przedmiotów** - linkowanie przedmiotów między kontenerami z automatyczną propagacją zmian

### Analityka i Statystyki
- ✅ **Obliczenia wagi:**
  - Całkowita waga plecaka z rekursywnym obliczaniem dla zagnieżdżonych kontenerów
  - Rozkład wagi według kategorii
  - Śledzenie wagi podstawowej vs. materiałów zużywalnych
  - Rozkład wagi według typu (Other/Worn/Consumable) - wizualizacja breakdown
- ✅ **Wskaźniki gotowości** - procent kompletności zestawu (posiadane vs. brakujące)
- ✅ **Wykresy pierścieniowe (donut)** - wizualny rozkład wagi, ilości, ceny lub priorytetu według kategorii
- ✅ **Statystyki przedmiotów** - liczenie według statusu, kategorii lub priorytetu
- ✅ **Automatyczny wybór jednostki wagi** - opcje `auto-g-kg` i `auto-oz-lb` z automatycznym wyborem jednostki w zależności od wartości
- ✅ **Formatowanie z separatorem tysięcznym** - formatowanie wag z separatorami tysięcy zgodnie z lokalizacją użytkownika

### Wyszukiwanie i Filtrowanie
- ✅ **Inteligentne wyszukiwanie** - znajdowanie przedmiotów po nazwie, marce lub notatkach we wszystkich kontenerach
- ✅ **Filtrowanie wielokryteriowe** - filtrowanie według kategorii, statusu, priorytetu lub kontenera
- ✅ **Opcje sortowania** - sortowanie według nazwy, wagi, daty ważności lub priorytetu
- ✅ **Podświetlanie przedmiotów przeterminowanych** - wizualne ostrzeżenia
- ✅ **Strona "Wszystkie przedmioty"** - dedykowana strona pokazująca wszystkie przedmioty ze wszystkich kontenerów
- ✅ **Strona planowania zakupów** - zarządzanie przedmiotami do kupienia i wkrótce przeterminowanymi

### Import/Export
- ✅ **Export/Import JSON** - pełna kopia zapasowa i przywracanie danych
- ✅ **Export do Markdown dla AI** - export kontenerów do formatu markdown dla przetwarzania przez AI
  - Strukturalny format z metadanymi (waga, marka, kolor, status)
  - Wsparcie dla zagnieżdżonych kontenerów z obliczonymi wagami
  - Legenda wyjaśniająca strukturę danych
  - Kopiowanie jednym kliknięciem do schowka
  - Opcje eksportu: format opisu (off/compact/full), separatory semantyczne, zachowanie pustych linii dla ChatGPT
- ✅ **Import z Markdown** - import kontenerów z plików markdown
  - Wsparcie dla UUID w eksporcie/impocie - aktualizacja istniejących kontenerów/przedmiotów po UUID
  - Tryb importu: aktualizacja istniejących (po UUID) vs tworzenie nowych
- ✅ **CSV Export** - eksport kontenerów do formatu CSV z wyborem kolumn, separatorów i kodowania UTF-8 z BOM dla Excel
- ✅ **Transfer między urządzeniami** - export z jednego urządzenia, import na drugim

### Galeria Zdjęć Przedmiotów
- ✅ **Upload zdjęć** - możliwość dodawania zdjęć do przedmiotów (wymaga uprawnień admina)
- ✅ **Upload z URL** - możliwość dodawania zdjęć z zewnętrznych URL (szczególnie przydatne dla adminów)
- ✅ **Wiele zdjęć na przedmiot** - galeria obrazów dla każdego przedmiotu (max 10)
- ✅ **Zmiana kolejności** - drag & drop do zmiany kolejności zdjęć
- ✅ **Główne zdjęcie** - oznaczanie zdjęcia jako głównego dla przedmiotu
- ✅ **Usuwanie zdjęć** - możliwość usunięcia pojedynczych zdjęć z galerii
- ✅ **Primary image w tabeli** - opcjonalne wyświetlanie miniaturki głównego zdjęcia w wierszach tabeli przedmiotów
- ✅ **Podgląd obrazów** - pełnoekranowy podgląd obrazów w galerii
- ✅ **Storage adapter pattern** - wsparcie dla local filesystem i S3 (Scaleway)
- ✅ **Automatyczne przetwarzanie** - resize, optymalizacja JPEG, walidacja formatów
- ✅ **Automatyczne usuwanie obrazów** - automatyczne usuwanie obrazów z S3/local storage przy usuwaniu przedmiotów, kontenerów, kont użytkowników
- ✅ **Limity** - maksymalny rozmiar pliku (10 MB), maksymalna liczba zdjęć na przedmiot (10)
- 🔄 **Automatyczne pobieranie zdjęć** - integracja z wyszukiwarkami obrazów (planowane)

### Cloud Storage (S3)
- ✅ **Scaleway S3 Integration** - wsparcie dla Scaleway jako providera S3
- ✅ **Local storage fallback** - lokalny filesystem dla środowiska deweloperskiego

---

## 👤 Profil Użytkownika

- ✅ **Zarządzanie profilem** - aktualizacja imienia, emaila i preferencji
- ✅ **Wsparcie dla avatarów** - dostawcy OAuth automatycznie dostarczają zdjęcia profilowe (Gravatar jako fallback)
- ✅ **Preferowane ustawienia** - jednostki wagi, język, motyw, preferencje wyświetlania
- ✅ **Ustawienia bezpieczeństwa** - zarządzanie metodami 2FA, wyświetlanie statusu bezpieczeństwa
- ✅ **Publiczny profil** - możliwość udostępnienia profilu publicznie z informacjami o użytkowniku i jego publicznych kontenerach
- ✅ **Oznaczenia ról** - wizualne oznaczenia ról użytkownika (Owner, Premium, Admin) z ikonami i kolorami

---

## 👥 Udostępnianie i Współpraca

### Publiczna Galeria Kontenerów
- ✅ **Przeglądarka publicznych kontenerów** - strona z listą wszystkich publicznie udostępnionych kontenerów (`PublicContainersBrowserPage`)
- ✅ **Filtrowanie i wyszukiwanie** - wyszukiwanie po nazwie, opisie, typie kontenera lub autorze
- ✅ **Strona szczegółów publicznego kontenera** - przeglądanie publicznego kontenera z wszystkimi przedmiotami (`PublicContainerDetailPage`)
- ✅ **Publiczna strona szczegółów przedmiotu** - wyświetlanie szczegółów przedmiotu w trybie publicznym (`PublicItemDetailPage`)
- ✅ **Backend endpoint** - API dla pobierania publicznych kontenerów (`/gear/public/containers`)
- ✅ **Pole publiczne w formularzu** - możliwość oznaczenia kontenera jako publiczny podczas tworzenia/edycji
- ✅ **System raportowania treści** - zgłaszanie nieodpowiednich treści w publicznych kontenerach przez zalogowanych użytkowników
  - Automatyczne ukrywanie kontenerów z widoków publicznych po ≥3 zgłoszeniach
  - Panel administracyjny do weryfikacji zgłoszeń
  - Kategorie zgłoszeń: Spam/Oszustwa, Przemoc, Treści seksualne, Wulgaryzmy, Inne

---

## 🔧 Panel Administracyjny

### Admin Dashboard (`/admin`)
- ✅ **Centralny panel admina** - przegląd wszystkich funkcji administracyjnych
- ✅ **Statystyki** - szybki dostęp do zarządzania użytkownikami, kontenerami i przedmiotami
- ✅ **Ochrona dostępu** - wymagane uprawnienia admina (`requiresAdmin: true`)

### Zarządzanie Użytkownikami (`/admin/users`)
- ✅ **Lista wszystkich użytkowników** - przegląd kont z paginacją
- ✅ **Wyszukiwanie użytkowników** - szybkie wyszukiwanie po nazwie lub emailu
- ✅ **Promowanie/degradowanie adminów** - zarządzanie uprawnieniami administratora
- ✅ **Role użytkowników** - system ról: Owner, Premium, Admin, User z odpowiednimi oznaczeniami
- ✅ **Ochrona użytkowników** - ochrona Owner i Admin przed usunięciem przez innych adminów
- ✅ **Usuwanie użytkowników** - możliwość usunięcia konta użytkownika z potwierdzeniem
- ✅ **Statusy użytkowników** - widoczność statusów: aktywny/nieaktywny, zweryfikowany/niezweryfikowany, role
- ✅ **Sortowanie i filtrowanie** - po dacie utworzenia, statusie, uprawnieniach

### Zarządzanie Limitami Funkcji (`/admin/limits`)
- ✅ **Konfiguracja limitów funkcji** - zarządzanie limitami AI i storage dla różnych ról użytkowników
- ✅ **Limity per rola** - konfigurowalne limity dla User, Premium, Admin, Owner
- ✅ **Limity AI** - limity użycia AI w USD (0$ dla User, 5$ dla Premium, unlimited dla Admin/Owner)
- ✅ **Limity Storage** - limity przestrzeni dyskowej (20MB User, 50MB Premium, 200MB Admin, 1GB Owner)

### Zarządzanie Kontenerami (`/admin/containers`)
- ✅ **Lista wszystkich kontenerów** - przegląd kontenerów wszystkich użytkowników
- ✅ **Wyszukiwanie kontenerów** - po nazwie, typie, autorze
- ✅ **Informacje o kontenerach** - typ, autor, status publiczny/prywatny, liczba przedmiotów
- ✅ **Usuwanie kontenerów** - możliwość usunięcia kontenera z potwierdzeniem
- ✅ **Filtrowanie** - po typie kontenera, statusie publicznym/prywatnym, autorze

### Zarządzanie Przedmiotami (`/admin/items`)
- ✅ **Lista wszystkich przedmiotów** - przegląd przedmiotów ze wszystkich kontenerów
- ✅ **Wyszukiwanie przedmiotów** - po nazwie, kategorii, kontenerze, autorze
- ✅ **Szczegółowe informacje** - nazwa, kategoria, kontener, autor, ilość, waga, status, priorytet
- ✅ **Usuwanie przedmiotów** - możliwość usunięcia przedmiotu z potwierdzeniem
- ✅ **Sortowanie** - po wszystkich kolumnach (nazwa, waga, data utworzenia, itp.)

### Zarządzanie Katalogiem (`/admin/catalogue`)
- ✅ **Zarządzanie globalnym katalogiem** - strona zarządzania przedmiotami w globalnym katalogu
- ✅ **Filtrowanie i wyszukiwanie** - wyszukiwanie po nazwie, kategorii, marce, statusie aktywności
- ✅ **Akcje na przedmiotach** - wyświetlanie, edycja, aktywacja/deaktywacja, usuwanie
- ✅ **Promowanie przedmiotów do katalogu** - system głosowania społecznościowego (≥10 promocji)
- ✅ **Wyświetlanie twórcy** - informacja o twórcy przedmiotu w katalogu (zgodnie z ustawieniami profilu publicznego)

---

## 🌐 Wielojęzyczność (i18n)

- ✅ **Pełne wsparcie dla języków** - angielski i polski
- ✅ **Automatyczne wykrywanie języka** - z ustawień przeglądarki
- ✅ **Ręczne przełączanie języka** - w ustawieniach
- ✅ **Pełna lokalizacja** - wszystkie teksty UI, komunikaty walidacji i emaile
- ✅ **Pluralizacja polska** - poprawne obsługiwanie form liczby mnogiej w języku polskim (0, 1, 2-4, 5+)

---

## 🎨 Wygląd i Doświadczenie Użytkownika

### Motywy
- ✅ **Tryb ciemny (Dark Mode)** - pełne wsparcie z automatycznym wykrywaniem preferencji systemowych
- ✅ **Persystencja motywu** - ustawienia zapisywane per użytkownik
- ✅ **Ikony kategorii** - dedykowane ikony dla każdej kategorii przedmiotów
- ✅ **Kolory kontenerów** - przypisywanie kolorów dla wizualnego odróżnienia

### Responsywność
- ✅ **Mobile-first design** - projektowanie najpierw dla urządzeń mobilnych
- ✅ **Adaptacyjny layout** - dostosowywanie się do różnych rozmiarów ekranów
- ✅ **Touch-friendly** - przyjazne dla ekranów dotykowych

---

## ⚡ Funkcje Produktywności

- ✅ **Szybkie wprowadzanie przedmiotów** - inteligentne domyślne wartości i skróty klawiszowe
- ✅ **Rozszerzalne wiersze** - rozwijanie w tabelach przedmiotów, aby zobaczyć zawartość zagnieżdżonych kontenerów
- ✅ **Preferowana jednostka wagi** - ustawienie użytkownika dla spójnego wyświetlania wag (g, kg, oz, lb, auto-g-kg, auto-oz-lb)
- ✅ **Limit maksymalnej wagi** - ustawianie maksymalnej wagi dla kontenerów z wizualnymi ostrzeżeniami
- ✅ **Strona 404** - przyjazna dla użytkownika strona "nie znaleziono" z sugestiami nawigacji
- ✅ **Footer i strony prawne** - informacje o cookies, zgodność z RODO, polityka prywatności
- ✅ **Dynamiczne tytuły stron** - automatyczne ustawianie tytułów stron w przeglądarce z nazwami kontenerów/przedmiotów
- ✅ **Sidebar Navigation** - nawigacja boczna z listą kontenerów i linkami, kompatybilna z LighterPack design
- ✅ **Markdown w notatkach i opisach** - pełne wsparcie Markdown w notatkach przedmiotów i opisach kontenerów z podglądem

---

## 🏗️ Architektura Techniczna

### Frontend
- **Vue 3.5+** z TypeScript i Composition API
- **Pinia** - zarządzanie stanem
- **Vue Router** - nawigacja
- **TailwindCSS v4** + shadcn-vue
- **VeeValidate + Zod** - walidacja formularzy
- **TanStack Query** - zarządzanie stanem serwera
- **vue-i18n** - internacjonalizacja

### Backend
- **FastAPI** (Python) z async/await
- **PostgreSQL** - baza danych
- **SQLAlchemy ORM** - z wsparciem async
- **JWT** - autentykacja z refresh tokens
- **Rate limiting** - ochrona przed nadmiernym ruchem
- **Modularna architektura** - auth, two-factor, email

### Infrastruktura
- **Docker** - konteneryzacja
- **Nginx** - reverse proxy
- **Docker Compose** - orkiestracja usług

### Progressive Web App (PWA)
- ✅ **Konwersja na PWA** - aplikacja dostępna jako Progressive Web App (`vite-plugin-pwa`)
- ✅ **Manifest.json** - pełna konfiguracja PWA z ikonami i metadanymi
- ✅ **Service Worker (Workbox)** - cache'owanie zasobów i offline support
- ✅ **Instalacja na urządzenia mobilne** - możliwość instalacji jak natywna aplikacja
- ✅ **Offline support** - podstawowa funkcjonalność działa offline dzięki cache'owaniu
- ✅ **Komponent aktualizacji** - `PwaUpdatePrompt` do powiadamiania o nowych wersjach
- ✅ **Runtime caching** - automatyczne cache'owanie dla API, fonts i assets
- ✅ **Responsywny design** - pełne wsparcie dla urządzeń mobilnych

---

## 📊 Persystencja Danych

### Hybrydowa Architektura
- ✅ **Client-side** - `localStorage` dla funkcjonalności offline-first
- ✅ **Server-side** - baza PostgreSQL dla synchronizacji między urządzeniami
- ✅ **Automatyczna synchronizacja** - zmiany synchronizują się z chmurą gdy online
- ✅ **Rozwiązywanie konfliktów** - inteligentne łączenie zmian offline

---

## 🤖 Funkcje AI

- ✅ **AI Chat Interface** - interfejs czatu z AI do interakcji z ekwipunkiem
- ✅ **Zarządzanie modelami AI** - wybór modelu AI (OpenRouter), zarządzanie tokenami API
- ✅ **Konfiguracja kontekstu** - konfiguracja kontekstu AI (wybór kontenerów, pól do uwzględnienia)
- ✅ **Historia konwersacji** - zapisywanie i przeglądanie historii konwersacji z AI
- ✅ **Szablony wiadomości** - szybkie szablony wiadomości do AI
- ✅ **Wyświetlanie kosztów** - wyświetlanie kosztów użycia AI (prompt/completion/total tokens)
- ✅ **Filtrowanie historii** - filtrowanie historii po kontenerach i typie operacji
- ✅ **Przywracanie konwersacji** - możliwość powrotu do poprzednich konwersacji z AI
- ✅ **Chat z listy kontenerów** - możliwość rozpoczęcia czatu z AI z automatycznym uwzględnieniem przefiltrowanych kontenerów
- 🔄 **Classification, embeddings, vision models** - planowane rozszerzenia AI

## 🔮 Planowane Funkcje (Roadmap)

### Wysokopriorytetowe
- ✅ **Edycja inline nazwy** - szybka edycja nazwy przedmiotu/kontenera (częściowo zakończone)
- 🔄 **Edycja inline pełna** - szybka edycja wszystkich pól przedmiotów bezpośrednio na liście
- ✅ **Kolejność przedmiotów** - ręczne ustawianie kolejności przedmiotów (zakończone)
- 🔄 **Drag & drop** - wizualne przeciąganie i upuszczanie do zmiany kolejności

### Średniopriorytetowe
- ✅ **Markdown w notatkach** - formatowane notatki (zakończone)

### Backend i Online
- 🚧 **Synchronizacja wielourządzeniowa** - automatyczna synchronizacja danych między urządzeniami (częściowo zakończone)
- ✅ **Udostępnianie kontenerów** - publiczne kontenery i token sharing (zakończone)
- ✅ **Globalny katalog przedmiotów** - baza wspólnych przedmiotów (zakończone)
- 🚧 **Funkcje AI** - chat, historia, zarządzanie modelami (częściowo zakończone)

---

## 🎯 Podsumowanie

Gear Stack to zaawansowana, bezpieczna aplikacja do zarządzania ekwipunkiem z:
- 🔐 **Profesjonalnym systemem bezpieczeństwa** (OAuth, 2FA, rate limiting, reCAPTCHA)
- 🎒 **Zaawansowanym zarządzaniem ekwipunkiem** (hierarchia, analityka, eksport AI)
- 🌐 **Pełną internacjonalizacją** (PL/EN)
- 📱 **Responsywnym designem** (mobile-first)
- ☁️ **Hybrydową architekturą** (offline + cloud sync)
- 🚀 **Nowoczesnym stackiem technologicznym** (Vue 3, FastAPI, PostgreSQL)

Idealny dla entuzjastów outdooru, preperów i osób planujących wyprawy survivalowe!
