# Plan Integracji API z Frontendem

## 📋 Przegląd

Dokument opisuje szczegółowy plan integracji istniejących endpointów API backendu z frontendem. Ten dokument uzupełnia [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md), który skupia się na podstawowej infrastrukturze (auth, feature flag).

**Status**: 🔄 W przygotowaniu  
**Zależności**: Wymaga ukończenia podstawowej integracji z [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md)

---

## 🎯 Cele

1. **Integracja endpointów Gear API** - Kontenery i przedmioty
2. **Integracja endpointów Settings API** - Ustawienia użytkownika
3. **Zachowanie kompatybilności** - Fallback do localStorage gdy backend wyłączony
4. **Synchronizacja danych** - Dwu-kierunkowa synchronizacja między frontendem a backendem
5. **Optymistyczne aktualizacje** - Szybki UX z synchronizacją w tle

---

## 📊 Mapowanie Endpointów

### Gear API (`/api/gear`)

#### Containers
| Endpoint | Metoda | Status | Frontend Service | Store Action |
|----------|--------|--------|-----------------|--------------|
| `/gear/containers` | POST | ✅ | `gearApiService.createContainer()` | `useGearStore.addContainer()` |
| `/gear/containers` | GET | ✅ | `gearApiService.getContainers()` | `useGearStore.setContainers()` |
| `/gear/containers/{id}` | GET | ✅ | `gearApiService.getContainer()` | - |
| `/gear/containers/{id}` | PATCH | ✅ | `gearApiService.updateContainer()` | `useGearStore.updateContainer()` |
| `/gear/containers/{id}` | DELETE | ✅ | `gearApiService.deleteContainer()` | `useGearStore.removeContainer()` |

#### Items
| Endpoint | Metoda | Status | Frontend Service | Store Action |
|----------|--------|--------|-----------------|--------------|
| `/gear/containers/{id}/items` | POST | ✅ | `gearApiService.createItem()` | - |
| `/gear/containers/{id}/items` | GET | ✅ | `gearApiService.getItems()` | - |
| `/gear/items/{id}` | GET | ✅ | `gearApiService.getItem()` | - |
| `/gear/items/{id}` | PATCH | ✅ | `gearApiService.updateItem()` | - |
| `/gear/items/{id}` | DELETE | ✅ | `gearApiService.deleteItem()` | - |

#### Statistics
| Endpoint | Metoda | Status | Frontend Service | Użycie |
|----------|--------|--------|-----------------|--------|
| `/gear/containers/{id}/stats/weight` | GET | ✅ | `gearApiService.getContainerWeight()` | Obliczenia wagi |
| `/gear/containers/{id}/stats/readiness` | GET | ✅ | `gearApiService.getContainerReadiness()` | Procent gotowości |

### Settings API (`/api/settings`)

| Endpoint | Metoda | Status | Frontend Service | Store Action |
|----------|--------|--------|-----------------|--------------|
| `/settings` | GET | ✅ | `settingsApiService.getSettings()` | `useSettingsStore.loadFromStorage()` |
| `/settings` | PATCH | ✅ | `settingsApiService.updateSettings()` | `useSettingsStore.updateSettings()` |

---

## 🏗️ Architektura Integracji

### Warstwa Serwisowa

```
┌─────────────────────────────────────────────────────────┐
│                    Composables                          │
│  (useGear, useSettings, useGearSettings)              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    Services                             │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ gearService  │  │ gearApiService│                    │
│  │ (localStorage)│  │ (API calls)   │                    │
│  └──────┬───────┘  └──────┬─────────┘                    │
│         │                 │                              │
│         └────────┬────────┘                              │
│                  │                                       │
│         ┌────────▼────────┐                             │
│         │  Feature Flag   │                             │
│         │ (useBackend())  │                             │
│         └─────────────────┘                             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    Stores (Pinia)                       │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ useGearStore │  │ useSettingsStore│                  │
│  └──────────────┘  └───────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### Strategia Implementacji

1. **Service Layer Pattern**:
   - `gearService` - główny serwis używany przez composables
   - `gearApiService` - warstwa API (już istnieje)
   - `gearService` wybiera między localStorage a API na podstawie feature flag

2. **Store Synchronization**:
   - Store zawsze przechowuje aktualne dane (single source of truth)
   - Service synchronizuje z backendem w tle
   - Optymistyczne aktualizacje UI

3. **Error Handling**:
   - Fallback do localStorage przy błędach API
   - Retry logic dla failed requests
   - Queue dla offline operations

---

## 📝 Plan Implementacji

### Faza 1: Przygotowanie Infrastruktury ✅

- [x] Utworzenie `gearApiService` z wszystkimi metodami
- [x] Utworzenie `settingsApiService`
- [x] Feature flag `VITE_ENABLE_BACKEND` w config
- [x] Composable `useBackend()` helper
- [ ] Utworzenie `useSyncStore` dla zarządzania synchronizacją

### Faza 2: Integracja Gear Service

#### 2.1. Refaktoryzacja `gearService`
- [ ] Dodanie warunkowego wyboru między localStorage a API
- [ ] Integracja `gearApiService` w `gearService`
- [ ] Synchronizacja store z odpowiedziami API
- [ ] Obsługa błędów i fallback

#### 2.2. Container Operations
- [ ] `createContainer()` - API + store update
- [ ] `getContainers()` - API fetch + store sync
- [ ] `updateContainer()` - API + store update
- [ ] `deleteContainer()` - API + store remove

#### 2.3. Item Operations
- [ ] `createItem()` - API + store update
- [ ] `getItems()` - API fetch + store sync
- [ ] `updateItem()` - API + store update
- [ ] `deleteItem()` - API + store remove

#### 2.4. Statistics
- [ ] Integracja endpointów statystyk
- [ ] Cache dla statystyk (opcjonalnie)

### Faza 3: Integracja Settings Service

- [ ] Refaktoryzacja `settingsService` z warunkowym wyborem
- [ ] Integracja `settingsApiService`
- [ ] Synchronizacja `useSettingsStore` z API
- [ ] Obsługa błędów i fallback

### Faza 4: Synchronizacja i Cache

#### 4.1. Initial Load
- [ ] Fetch wszystkich kontenerów przy starcie (gdy backend enabled)
- [ ] Merge z localStorage (migracja danych)
- [ ] Conflict resolution

#### 4.2. Real-time Sync
- [ ] Auto-refresh przy focus window
- [ ] Polling dla zmian (opcjonalnie)
- [ ] WebSocket integration (future)

#### 4.3. Offline Support
- [ ] Queue dla operacji offline
- [ ] Sync queue przy powrocie online
- [ ] Conflict resolution strategy

### Faza 5: Optymalizacje

- [ ] Optymistyczne aktualizacje UI
- [ ] Debouncing dla częstych operacji
- [ ] Cache invalidation strategy
- [ ] Loading states i skeletons

### Faza 6: Testowanie

- [ ] Testy jednostkowe dla service layer
- [ ] Testy integracyjne z mock API
- [ ] E2E testy z prawdziwym backendem
- [ ] Testy offline/online transitions

---

## 🔧 Szczegóły Implementacji

### Przykład: Refaktoryzacja `gearService.createContainer()`

**Przed (tylko localStorage):**
```typescript
createContainer(data: ICreateContainerDto): IGearContainer {
  const container = { /* ... */ }
  this.store.addContainer(container)
  return container
}
```

**Po (z feature flag):**
```typescript
async createContainer(data: ICreateContainerDto): Promise<IGearContainer> {
  const { isBackendEnabled } = useBackend()
  
  if (isBackendEnabled.value) {
    try {
      // API call
      const container = await gearApiService.createContainer(data)
      // Update store with server response
      this.store.addContainer(container)
      return container
    } catch (error) {
      // Fallback to localStorage
      console.warn('API failed, falling back to localStorage', error)
      return this.createContainerLocal(data)
    }
  }
  
  // Offline mode
  return this.createContainerLocal(data)
}

private createContainerLocal(data: ICreateContainerDto): IGearContainer {
  const container = { /* ... */ }
  this.store.addContainer(container)
  return container
}
```

### Przykład: Initial Load z Synchronizacją

```typescript
async loadContainers(): Promise<void> {
  const { isBackendEnabled } = useBackend()
  
  if (isBackendEnabled.value) {
    try {
      // Fetch from API
      const containers = await gearApiService.getContainers()
      this.store.setContainers(containers)
      
      // Optional: Migrate localStorage data to backend
      await this.migrateLocalStorageToBackend()
    } catch (error) {
      console.error('Failed to load from API, using localStorage', error)
      this.store.loadFromStorage()
    }
  } else {
    // Offline mode
    this.store.loadFromStorage()
  }
}
```

---

## 🔄 Migracja Danych

### Strategia Migracji

1. **Przy pierwszym logowaniu**:
   - Sprawdź czy są dane w localStorage
   - Jeśli tak, zaproponuj migrację
   - Użytkownik może wybrać: "Migruj teraz" / "Później" / "Nie migruj"

2. **Automatyczna migracja** (opcjonalnie):
   - W tle przy starcie aplikacji
   - Merge strategy: backend wins / local wins / manual

3. **Eksport/Import**:
   - Użytkownik może wyeksportować dane z localStorage
   - Import przez API endpoint (jeśli istnieje)

### Conflict Resolution

- **Timestamp-based**: Najnowsza wersja wygrywa
- **User choice**: Pokaż konflikty użytkownikowi
- **Merge strategy**: Inteligentne łączenie zmian

---

## 🚨 Uwagi i Ostrzeżenia

1. **Type Safety**: Wszystkie typy z backendu muszą być zsynchronizowane z frontendem
2. **Error Handling**: Zawsze fallback do localStorage przy błędach
3. **Performance**: Unikaj niepotrzebnych API calls (cache, debouncing)
4. **Security**: Wszystkie endpointy wymagają autentykacji
5. **Offline First**: Aplikacja musi działać bez backendu

---

## 📚 Zasoby

- [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) - Podstawowa infrastruktura
- [ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md) - Funkcjonalności wymagające backendu
- Backend API docs: `backend/README.md`
- Frontend services: `src/modules/gear/services/`

---

## ✅ Checklist

### Przed rozpoczęciem
- [ ] BACKEND_INTEGRATION.md - Faza 1-6 ukończona (auth działa)
- [ ] Backend uruchomiony i dostępny
- [ ] Feature flag działa poprawnie
- [ ] Wszystkie typy zsynchronizowane

### Podczas implementacji
- [ ] Każda operacja ma fallback do localStorage
- [ ] Wszystkie błędy są obsłużone gracefully
- [ ] Store zawsze w sync z API
- [ ] Testy dla każdej operacji

### Przed merge
- [ ] Tryb offline działa jak wcześniej
- [ ] Tryb online działa poprawnie
- [ ] Migracja danych działa
- [ ] Brak console errors
- [ ] Performance acceptable

---

**Data utworzenia**: 2025-01-27  
**Status**: 🔄 W przygotowaniu  
**Ostatnia aktualizacja**: 2025-01-27

