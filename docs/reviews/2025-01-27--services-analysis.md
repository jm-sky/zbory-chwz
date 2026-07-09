# Analiza Serwisów - Pattern Interface + ApiService

## 📋 Przegląd

Dokument analizuje wszystkie serwisy w projekcie i weryfikuje czy stosują wzorzec:
- **Interface** w `*.type.ts` - definicja kontraktu
- **LocalStorage Service** - implementacja dla trybu offline
- **ApiService** - implementacja dla trybu online (gdy backend enabled)

---

## 📊 Status Serwisów

### ✅ Settings Service

**Status**: ⚠️ Częściowo zgodne

- ✅ `ISettingsService` interface w `settings.type.ts`
- ✅ `settingsApiService.ts` implementuje `ISettingsService`
- ❌ `settingsService.ts` (localStorage) **NIE** implementuje interfejsu - to klasa statyczna

**Problem**: `SettingsService` używa metod statycznych zamiast instancji z interfejsem.

**Rozwiązanie**: 
- Opcja 1: Refaktoryzacja `SettingsService` na instancję implementującą `ISettingsService`
- Opcja 2: Stworzenie wrappera `SettingsLocalService` implementującego interfejs

---

### ✅ Auth Service

**Status**: ✅ Zgodne (tylko API)

- ✅ `IAuthService` interface w `auth.type.ts`
- ✅ `authService.ts` implementuje `IAuthService`
- ℹ️ Brak localStorage wersji (auth wymaga backendu)

**Uwaga**: Auth zawsze wymaga backendu, więc brak localStorage wersji jest OK.

---

### ❌ Gear Service

**Status**: ❌ Brak interfejsu

- ❌ Brak `IGearService` interface w `gear.types.ts`
- ❌ `gearService.ts` (localStorage) - klasa bez interfejsu
- ✅ `gearApiService.ts` istnieje ale nie implementuje interfejsu

**Problem**: Brak wspólnego interfejsu dla obu implementacji.

**Rozwiązanie**:
1. Stworzyć `IGearService` interface w `gear.types.ts`
2. Refaktoryzacja `gearService.ts` aby implementował interfejs
3. Refaktoryzacja `gearApiService.ts` aby implementował interfejs

---

### ❌ Gear Settings Service

**Status**: ❌ Brak interfejsu i ApiService

- ❌ Brak `IGearSettingsService` interface
- ❌ `gearSettingsService.ts` (localStorage) - klasa statyczna
- ❌ Brak `gearSettingsApiService.ts`

**Problem**: 
- Brak interfejsu
- Brak ApiService (backend nie ma endpointów dla gear settings na razie)

**Rozwiązanie**:
1. Stworzyć `IGearSettingsService` interface w `gearSettings.types.ts`
2. Refaktoryzacja `gearSettingsService.ts` na instancję z interfejsem
3. ApiService - **opcjonalnie** gdy backend będzie miał endpointy

---

### ✅ Two Factor Service

**Status**: ✅ Zgodne (tylko API)

- ✅ `ITwoFactorService` interface w `twoFactor.type.ts`
- ✅ `twoFactorService.ts` implementuje `ITwoFactorService`
- ℹ️ Brak localStorage wersji (2FA wymaga backendu)

**Uwaga**: 2FA zawsze wymaga backendu, więc brak localStorage wersji jest OK.

---

### ℹ️ Markdown Import Service

**Status**: ℹ️ Utility service (nie wymaga interfejsu)

- `markdownImportService.ts` - utility service do importu markdown
- Nie wymaga interfejsu ani ApiService (działa lokalnie)

---

## 🎯 Plan Naprawy

### Priorytet 1: Gear Service (wysoki priorytet)

1. **Stworzyć `IGearService` interface** w `gear.types.ts`
   ```typescript
   export interface IGearService {
     // Containers
     createContainer(data: ICreateContainerDto): Promise<IGearContainer>
     getContainers(skip?: number, limit?: number): Promise<IGearContainer[]>
     getContainer(id: TUUID): Promise<IGearContainer>
     updateContainer(id: TUUID, data: IUpdateContainerDto): Promise<IGearContainer>
     deleteContainer(id: TUUID): Promise<void>
     
     // Items
     createItem(containerId: TUUID, data: ICreateItemDto): Promise<IGearItem>
     getItems(containerId: TUUID, skip?: number, limit?: number): Promise<IGearItem[]>
     getItem(itemId: TUUID): Promise<IGearItem>
     updateItem(itemId: TUUID, data: IUpdateItemDto): Promise<IGearItem>
     deleteItem(itemId: TUUID): Promise<void>
     
     // Statistics
     getContainerWeight(containerId: TUUID): Promise<{ grams: number; kilograms: number }>
     getContainerReadiness(containerId: TUUID): Promise<{...}>
   }
   ```

2. **Refaktoryzacja `gearService.ts`**
   - Zmienić z klasy na instancję implementującą `IGearService`
   - Wszystkie metody async (nawet dla localStorage)
   - Warunkowy wybór między localStorage a API przez feature flag

3. **Refaktoryzacja `gearApiService.ts`**
   - Dodać implementację `IGearService`
   - Upewnić się że wszystkie metody są zgodne z interfejsem

### Priorytet 2: Settings Service (średni priorytet)

1. **Refaktoryzacja `settingsService.ts`**
   - Opcja A: Zmienić na instancję implementującą `ISettingsService`
   - Opcja B: Stworzyć `SettingsLocalService` wrapper

2. **Upewnić się że obie wersje są używane warunkowo**
   ```typescript
   const service = config.backend.enabled 
     ? settingsApiService 
     : settingsLocalService
   ```

### Priorytet 3: Gear Settings Service (niski priorytet)

1. **Stworzyć `IGearSettingsService` interface** w `gearSettings.types.ts`
2. **Refaktoryzacja `gearSettingsService.ts`** na instancję z interfejsem
3. **ApiService** - tylko gdy backend będzie miał endpointy

---

## 📝 Przykład Refaktoryzacji

### Przed (gearService.ts):
```typescript
class GearService {
  createContainer(data: ICreateContainerDto): IGearContainer {
    const container = { /* ... */ }
    this.store.addContainer(container)
    return container
  }
}

export const gearService = new GearService()
```

### Po (gearService.ts):
```typescript
import type { IGearService } from '../types/gear.types'
import { gearApiService } from './gearApiService'
import { useBackend } from '@/shared/composables/useBackend'

class GearLocalService implements IGearService {
  // localStorage implementation
  async createContainer(data: ICreateContainerDto): Promise<IGearContainer> {
    const container = { /* ... */ }
    this.store.addContainer(container)
    return container
  }
  // ... other methods
}

class GearService implements IGearService {
  private localService = new GearLocalService()
  private { isBackendEnabled } = useBackend()

  async createContainer(data: ICreateContainerDto): Promise<IGearContainer> {
    if (isBackendEnabled.value) {
      try {
        return await gearApiService.createContainer(data)
      } catch (error) {
        console.warn('API failed, falling back to localStorage', error)
        return await this.localService.createContainer(data)
      }
    }
    return await this.localService.createContainer(data)
  }
  // ... other methods with same pattern
}

export const gearService = new GearService()
```

---

## ✅ Checklist

### Gear Service
- [ ] Stworzyć `IGearService` interface
- [ ] Refaktoryzacja `gearService.ts` na instancję z interfejsem
- [ ] Refaktoryzacja `gearApiService.ts` aby implementował interfejs
- [ ] Warunkowy wybór między localStorage a API
- [ ] Testy dla obu implementacji

### Settings Service
- [ ] Refaktoryzacja `settingsService.ts` na instancję z interfejsem
- [ ] Warunkowy wybór między localStorage a API
- [ ] Testy dla obu implementacji

### Gear Settings Service
- [ ] Stworzyć `IGearSettingsService` interface
- [ ] Refaktoryzacja `gearSettingsService.ts` na instancję z interfejsem
- [ ] ApiService (opcjonalnie gdy backend będzie miał endpointy)

---

## 📚 Zasoby

- [API_INTEGRATION_PLAN.md](./API_INTEGRATION_PLAN.md) - Plan integracji API
- [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) - Podstawowa infrastruktura

---

**Data utworzenia**: 2025-01-27  
**Status**: 🔄 W przygotowaniu  
**Ostatnia aktualizacja**: 2025-01-27

