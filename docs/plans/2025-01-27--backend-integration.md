# Plan Integracji z Backendem

## 📋 Przegląd

Dokument opisuje plan integracji frontendu `gear-stack` z backendem FastAPI. Integracja będzie wzorowana na projekcie `../test`, który zawiera sprawdzone wzorce implementacji modułu autentykacji i innych funkcjonalności.

## 🎯 Cele

1. **Integracja autentykacji** - Logowanie, rejestracja, zarządzanie sesją
2. **Zachowanie kompatybilności** - Obecna wersja działająca bez backendu musi pozostać funkcjonalna
3. **Kontrola przez feature flag** - Włączanie/wyłączanie integracji przez zmienną środowiskową
4. **Bezpieczna implementacja** - Stopniowe wprowadzanie zmian bez psucia obecnej wersji

## 📁 Struktura Projektów

### Projekt referencyjny: `../test`
```
test/
├── backend/          # FastAPI backend (fastapi-blocks-registry)
│   └── app/
│       └── modules/
│           └── auth/  # Moduł autentykacji
└── frontend/          # Vue frontend (vue-blocks-registry)
    └── src/
        ├── modules/
        │   └── auth/  # Pełna implementacja auth
        └── shared/
            └── services/
                ├── apiClient.ts
                ├── auth.interceptor.ts
                └── error.interceptor.ts
```

### Nasz projekt: `gear-stack`
```
gear-stack/
├── backend/          # Backend skopiowany z test (fastapi-blocks-registry)
└── src/
    └── shared/
        └── services/
            ├── apiClient.ts          # ✅ Już istnieje
            ├── auth.interceptor.ts   # ✅ Już istnieje (podstawowa wersja)
            └── error.interceptor.ts  # ✅ Już istnieje (uproszczona wersja)
```

## 🔍 Analiza Różnic

### Co już mamy w `gear-stack`:
- ✅ Podstawowy `apiClient` z axios
- ✅ Podstawowy `auth.interceptor` (dodaje token do nagłówków)
- ✅ Uproszczony `error.interceptor` (tylko czyszczenie localStorage przy 401)

### Co trzeba dodać z projektu `test`:

#### 1. Moduł Auth (`src/modules/auth/`)
```
modules/auth/
├── components/
│   ├── LoginForm.vue
│   └── RegisterForm.vue
├── composables/
│   └── useAuth.ts (opcjonalnie)
├── config/
│   ├── auth.config.ts
│   └── routes.ts
├── guards/
│   └── authGuard.ts
├── pages/
│   ├── LoginPage.vue
│   └── RegisterPage.vue
├── services/
│   └── authService.ts
├── store/
│   └── useAuthStore.ts
├── types/
│   ├── auth.type.ts
│   └── user.type.ts
└── utils/
    └── token.utils.ts (opcjonalnie)
```

#### 2. Ulepszenia w `shared/services/`
- **error.interceptor.ts**: 
  - Automatyczne odświeżanie tokenów
  - Kolejkowanie żądań podczas refresh
  - Integracja z login modal
- **auth.interceptor.ts**: 
  - Może pozostać bez zmian (już działa)

#### 3. Nowe store w `shared/store/`
- `useTokenRefreshStore.ts` - Zarządzanie stanem odświeżania tokenów

#### 4. Routing
- Dodanie tras `/login`, `/register`
- Implementacja guardów dla chronionych tras
- Meta `requiresAuth` i `requiresGuest`

## 🚩 Feature Flag

### Zmienna środowiskowa: `VITE_ENABLE_BACKEND`

```env
# .env
VITE_ENABLE_BACKEND=false  # Domyślnie wyłączone (tryb offline)
```

### Użycie w kodzie:

```typescript
// src/shared/config/config.ts
export const config = {
  // ... istniejące config
  backend: {
    enabled: import.meta.env.VITE_ENABLE_BACKEND === 'true',
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
  },
}

// W komponentach/serwisach
import { config } from '@/shared/config/config'

if (config.backend.enabled) {
  // Użyj backend API
  await authService.login(credentials)
} else {
  // Użyj localStorage (obecna implementacja)
  // ...
}
```

### Strategia implementacji:

1. **Tryb offline (domyślny)**: 
   - `VITE_ENABLE_BACKEND=false`
   - Wszystko działa jak dotychczas (localStorage)
   - Brak zmian w UX

2. **Tryb online**:
   - `VITE_ENABLE_BACKEND=true`
   - Wymagane: `VITE_API_BASE_URL=http://localhost:8000/api`
   - Frontend komunikuje się z backendem
   - Dane synchronizowane z serwerem

## 📝 Plan Implementacji

### Faza 1: Przygotowanie (bez zmian w kodzie)
- [x] Utworzenie dokumentu integracji
- [x] Utworzenie brancha `feature/backend-integration`
- [ ] Analiza szczegółowa różnic w kodzie

### Faza 2: Infrastruktura (feature flag)
- [ ] Dodanie `VITE_ENABLE_BACKEND` do `.env.example`
- [ ] Rozszerzenie `config.ts` o konfigurację backendu
- [ ] Utworzenie helpera `useBackend()` composable

### Faza 3: Moduł Auth - Typy i Serwisy
- [ ] Skopiowanie typów z `test/frontend/src/modules/auth/types/`
- [ ] Implementacja `authService.ts` (z feature flag)
- [ ] Ulepszenie `error.interceptor.ts` (automatyczny refresh token)
- [ ] Utworzenie `useTokenRefreshStore.ts`

### Faza 4: Moduł Auth - Store i State
- [ ] Implementacja `useAuthStore.ts` (Pinia)
- [ ] Integracja z localStorage (fallback dla trybu offline)
- [ ] Synchronizacja tokenów między store a localStorage

### Faza 5: Moduł Auth - UI
- [ ] Komponenty: `LoginForm.vue`, `RegisterForm.vue`
- [ ] Strony: `LoginPage.vue`, `RegisterPage.vue`
- [ ] Integracja z istniejącym UI (Shadcn-Vue)

### Faza 6: Routing i Guards
- [ ] Dodanie tras `/login`, `/register`
- [ ] Implementacja `authGuard.ts`
- [ ] Oznaczenie chronionych tras (`meta.requiresAuth`)
- [ ] Redirect logic po logowaniu

### Faza 7: Integracja z istniejącym kodem
- [ ] Warunkowe użycie backendu w istniejących komponentach
- [ ] Migracja danych z localStorage do backendu (opcjonalnie)
- [ ] Obsługa błędów i fallback do trybu offline

### Faza 8: Testowanie i Dokumentacja
- [ ] Testowanie implementacji z użyciem Playwright/browser MCP
- [ ] Aktualizacja README.md
- [ ] Dokumentacja zmiennych środowiskowych

## 🧪 Testowanie Podczas Implementacji

Podczas implementacji będziemy używać **Playwright** lub **browser MCP** do interaktywnego testowania funkcjonalności w przeglądarce. To pozwoli na:

1. **Weryfikację działania w czasie rzeczywistym** - Sprawdzanie czy formularze działają, czy routing działa poprawnie
2. **Testowanie flow autentykacji** - Logowanie, rejestracja, wylogowanie
3. **Sprawdzanie guardów** - Czy chronione trasy są właściwie zabezpieczone
4. **Weryfikacja feature flag** - Czy tryb offline i online działają poprawnie

### Narzędzia do testowania

- **Playwright** - Do automatycznego testowania w przeglądarce
- **Browser MCP** - Do interaktywnego testowania przez AI
- **DevTools** - Do debugowania i sprawdzania network requests

### Scenariusze do przetestowania

1. **Rejestracja użytkownika** - Formularz, walidacja, sukces
2. **Logowanie** - Poprawne/niepoprawne dane, token w localStorage
3. **Chronione trasy** - Przekierowania, guardy
4. **Odświeżanie tokenu** - Automatyczny refresh przy 401
5. **Wylogowanie** - Czyszczenie danych, przekierowanie
6. **Feature flag** - Przełączanie między trybem offline/online

## 🔄 Migracja Danych (Opcjonalnie)

Gdy użytkownik przełączy się z trybu offline na online, można zaimplementować migrację danych:

1. **Eksport z localStorage** - Użytkownik może wyeksportować dane jako JSON
2. **Import przez API** - Endpoint `/api/containers/import` przyjmuje JSON
3. **Automatyczna synchronizacja** - Opcjonalnie: automatyczne wysłanie danych przy pierwszym logowaniu

## 🚨 Uwagi i Ostrzeżenia

1. **Nie psuj obecnej wersji** - Wszystkie zmiany muszą być warunkowe przez feature flag
2. **Fallback do localStorage** - Gdy backend nie jest dostępny, użyj localStorage
3. **Obsługa błędów** - Graceful degradation przy problemach z backendem
4. **Type safety** - Wszystkie typy z backendu powinny być zsynchronizowane
5. **Security** - Tokeny przechowywane bezpiecznie, refresh token rotation

## 🔗 Następne Kroki

Po ukończeniu podstawowej integracji (auth, feature flag), następnym krokiem jest integracja endpointów API:

- **[API_INTEGRATION_PLAN.md](./API_INTEGRATION_PLAN.md)** - Szczegółowy plan integracji endpointów Gear i Settings API z frontendem
- **[ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md)** - Roadmap funkcjonalności wymagających backendu (synchronizacja, udostępnianie, katalog, itp.)

## 📚 Zasoby

- Projekt referencyjny: `../test`
- Backend docs: `backend/README.md`
- FastAPI Blocks Registry: [dokumentacja scaffoldu]
- Vue Blocks Registry: [dokumentacja scaffoldu]

## ✅ Checklist przed merge

- [ ] Feature flag działa poprawnie
- [ ] Tryb offline (bez backendu) działa jak wcześniej
- [ ] Tryb online (z backendem) działa poprawnie
- [ ] Funkcjonalność przetestowana w przeglądarce (Playwright/browser MCP)
- [ ] Dokumentacja zaktualizowana
- [ ] `.env.example` zawiera wszystkie potrzebne zmienne
- [ ] Brak console errors w trybie offline
- [ ] Brak console errors w trybie online

---

**Data utworzenia**: 2025-01-27  
**Status**: W przygotowaniu  
**Branch**: `feature/backend-integration` (do utworzenia)

