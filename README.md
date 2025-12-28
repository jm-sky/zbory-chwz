# Zbory CHWZ

Aplikacja do publicznej prezentacji oraz zarządzania bazą adresów zborów CHWZ (Chrześcijańska Wspólnota Wolnych Zielonoświątkowców) z możliwością edycji danych przez uprawnione osoby.

## Domeny
- **zbory.chwz.waw.pl** *(preferowana)*
- **adresy.chwz.waw.pl** *(alternatywna)*

## Opis projektu

Zbory CHWZ to aplikacja webowa umożliwiająca:
- **Publiczną prezentację** - Wyszukiwanie zborów, mapa z lokalizacjami, publiczne profile zborów
- **Zarządzanie danymi** - System multi-tenant dla zarządzania danymi zborów przez uprawnione osoby
- **Administracja** - Pełny dostęp superadmina, model uprawnień per zbór

## Funkcjonalności

### Widoki publiczne
- Strona główna
- Wyszukiwarka zborów
- Mapa z pinezkami (Google Maps)
- Publiczne profile zborów (read-only)

### Dane zboru
- Nazwa
- Adres i miejscowość
- Strona internetowa (opcjonalnie)
- Telefon kontaktowy (opcjonalnie)
- Adres e-mail (opcjonalnie)

### Osoby kontaktowe (1..n)
- Imię, nazwisko
- Telefon, e-mail
- Rola (pastor, diakon, ewangelista, inne)

### Nabożeństwa (1..n)
- Dzień tygodnia
- Godzina
- Możliwość wielu nabożeństw jednego dnia

### System użytkowników
- **Superadmin** - pełny dostęp do wszystkich danych
- **Użytkownicy** - przypisanie do wielu zborów z różnymi rolami per zbór
- Relacja many-to-many: użytkownik ↔ zbór

## Stack technologiczny

### Frontend
- Vue 3.5+ z TypeScript i Composition API
- Pinia dla zarządzania stanem
- Vue Router dla nawigacji
- TailwindCSS v4 + shadcn-vue (komponenty UI)
- TanStack Query dla zarządzania stanem serwerowym
- vue-i18n dla wielojęzyczności

### Backend
- FastAPI (Python) z async/await
- PostgreSQL jako baza danych
- SQLAlchemy ORM z wsparciem async
- JWT authentication z refresh tokens
- Google reCAPTCHA dla ochrony
- Redis dla cache i blacklist tokenów

### Infrastruktura
- Docker containerization
- Nginx reverse proxy
- Konfiguracje development i production

## Rozpoczęcie pracy

### Wymagania
- Node.js ^20.19.0 lub >=22.12.0
- pnpm 10.18.3+
- Python 3.12+
- PostgreSQL 15+
- Docker & Docker Compose

### Frontend Development
```bash
pnpm install
pnpm dev              # Uruchom serwer dev (http://localhost:5176)
pnpm build            # Build produkcyjny
pnpm type-check       # Sprawdzenie TypeScript
pnpm lint             # ESLint z auto-fix
```

### Backend Development
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # lub `.venv\Scripts\activate` na Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Docker (Full Stack)
```bash
cd backend
docker compose -f docker-compose.dev.yml up
```

**UWAGA:** W development używaj `docker compose` (V2), nie `docker-compose` (V1 - deprecated).

## Zmienne środowiskowe

Skopiuj `.env.example` i dostosuj:

**Frontend (.env):**
```env
VITE_API_PROXY_URL=http://localhost:8000
VITE_GOOGLE_RECAPTCHA_SITE_KEY=your_recaptcha_site_key
```

**Backend (backend/.env):**
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/zbory_chwz
SECRET_KEY=your-secret-key
RECAPTCHA_ENABLED=true
RECAPTCHA_SECRET_KEY=your_recaptcha_secret
GOOGLE_OAUTH_CLIENT_ID=your_oauth_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_oauth_client_secret
```

## Struktura projektu

```
zbory-chwz/
├── src/                      # Frontend source code
│   ├── modules/              # Moduły funkcjonalne
│   │   ├── auth/             # Moduł uwierzytelniania
│   │   ├── admin/            # Panel administracyjny
│   │   ├── settings/         # Ustawienia
│   │   └── user/             # Profil użytkownika
│   ├── components/           # Współdzielone komponenty
│   │   └── ui/               # shadcn-vue komponenty
│   ├── layouts/              # Layout wrappers
│   ├── router/               # Vue Router config
│   └── shared/               # Narzędzia współdzielone
├── backend/                  # Backend source code
│   ├── app/
│   │   ├── core/             # Funkcjonalność podstawowa
│   │   ├── modules/          # Moduły funkcjonalne
│   │   │   ├── auth/         # Moduł uwierzytelniania
│   │   │   └── ...
│   │   └── main.py           # FastAPI app entry
│   └── migrations/           # Migracje bazy danych
└── docker-compose.yml        # Konfiguracja Docker
```

## Architektura

### Moduły Frontend
Każda funkcjonalność jest samodzielnym modułem w `src/modules/`:
- `pages/` - Komponenty stron Vue
- `components/` - Komponenty specyficzne dla modułu
- `store/` - Store Pinia dla stanu
- `services/` - Warstwa logiki biznesowej
- `types/` - Definicje TypeScript
- `routes.ts` - Routing modułu
- `i18n/` - Tłumaczenia modułu

### Moduły Backend
Backend zgodny z wzorcem modularnym FastAPI:
- `router.py` - Endpointy API
- `service.py` - Logika biznesowa
- `repositories.py` - Dostęp do bazy danych
- `models.py` - Modele domenowe
- `schemas.py` - Schematy request/response
- `db_models.py` - Modele SQLAlchemy

## Status projektu

Projekt jest w **fazie inicjalizacji**. Bazuje na boilerplate aplikacji do zarządzania ekwipunkiem survivalowym, dostosowanym do potrzeb zarządzania danymi zborów CHWZ.

Planowane jest iteracyjne rozwijanie funkcjonalności zgodnie z potrzebami społeczności CHWZ.

## Licencja

[Do ustalenia]

## Kontakt

W przypadku pytań lub propozycji funkcjonalności, prosimy o kontakt przez GitHub Issues.
