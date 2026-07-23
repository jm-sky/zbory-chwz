# FEATURE-029: Account Limits (Limity Kont)

**Status:** 🔄 Planned  
**Priority:** Medium  
**Category:** 💳 Account Management / Limits  
**Related:** ROADMAP_ONLINE.md - Limity przedmiotów i kontenerów dla kont free/premium

---

## 📋 Overview

Implementacja systemu limitów liczby przedmiotów i kontenerów w zależności od typu konta (free/premium), z możliwością opcjonalnego uwzględnienia wykorzystanej przestrzeni w bazie danych.

---

## 🎯 Goals

1. **System tierów kont** - rozróżnienie między kontami free i premium
2. **Limity liczbowe** - kontrola liczby przedmiotów i kontenerów per tier
3. **Walidacja limitów** - sprawdzanie limitów przy tworzeniu przedmiotów/kontenerów
4. **UI informacyjne** - wyświetlanie limitów i wykorzystania w ustawieniach użytkownika
5. **Opcjonalnie:** Monitoring wykorzystanej przestrzeni DB per użytkownik

---

## 🔍 Current State

### Brak implementacji
- Brak pola `account_tier` w tabeli `users`
- Brak walidacji limitów przy tworzeniu przedmiotów/kontenerów
- Brak UI do wyświetlania limitów
- Brak endpointów do sprawdzania limitów

---

## 📝 Implementation Plan

### Phase 1: Backend - Database & Models

#### Step 1.1: Dodanie pola `account_tier` do modelu użytkownika

**File:** `backend/app/modules/auth/db_models.py`

Dodaj pole do modelu `UserDB`:

```python
account_tier: Mapped[str] = mapped_column(
    String(20),
    default="free",
    nullable=False,
    server_default="free"
)
```

**Wartości:**
- `free` - darmowe konto (domyślne)
- `premium` - konto premium

#### Step 1.2: Migracja bazy danych

**File:** `backend/alembic/versions/XXXX_add_account_tier.py`

Utwórz migrację dodającą kolumnę `account_tier` do tabeli `users`.

#### Step 1.3: Konfiguracja limitów

**File:** `backend/app/modules/gear/config.py` (lub nowy plik)

```python
from pydantic import BaseModel

class AccountLimits(BaseModel):
    """Limits configuration for account tiers."""
    
    free_items: int = 500
    free_containers: int = 10
    premium_items: int = 1000
    premium_containers: int = 50

ACCOUNT_LIMITS = AccountLimits()
```

---

### Phase 2: Backend - Service Layer

#### Step 2.1: Service do sprawdzania limitów

**File:** `backend/app/modules/gear/services/limits_service.py`

```python
from app.modules.auth.db_models import UserDB
from app.modules.gear.config import ACCOUNT_LIMITS

class LimitsService:
    @staticmethod
    async def get_user_limits(user: UserDB) -> dict:
        """Get limits for user based on account tier."""
        tier = user.account_tier or "free"
        
        if tier == "premium":
            return {
                "items": ACCOUNT_LIMITS.premium_items,
                "containers": ACCOUNT_LIMITS.premium_containers,
            }
        else:
            return {
                "items": ACCOUNT_LIMITS.free_items,
                "containers": ACCOUNT_LIMITS.free_containers,
            }
    
    @staticmethod
    async def check_item_limit(user: UserDB, current_count: int) -> bool:
        """Check if user can create more items."""
        limits = await LimitsService.get_user_limits(user)
        return current_count < limits["items"]
    
    @staticmethod
    async def check_container_limit(user: UserDB, current_count: int) -> bool:
        """Check if user can create more containers."""
        limits = await LimitsService.get_user_limits(user)
        return current_count < limits["containers"]
```

#### Step 2.2: Endpoint do sprawdzania limitów

**File:** `backend/app/modules/gear/router.py`

```python
@router.get("/me/limits", response_model=UserLimitsResponse)
async def get_user_limits(
    current_user: CurrentUser,
    gear_repo: GearRepository = Depends(get_gear_repository),
    limits_service: LimitsService = Depends(get_limits_service),
):
    """Get user limits and current usage."""
    # Get current counts
    items_count = await gear_repo.count_user_items(current_user.id)
    containers_count = await gear_repo.count_user_containers(current_user.id)
    
    # Get limits
    limits = await limits_service.get_user_limits(current_user)
    
    return {
        "tier": current_user.account_tier or "free",
        "limits": limits,
        "usage": {
            "items": items_count,
            "containers": containers_count,
        },
        "percentage": {
            "items": (items_count / limits["items"]) * 100,
            "containers": (containers_count / limits["containers"]) * 100,
        },
    }
```

#### Step 2.3: Walidacja limitów przy tworzeniu

**File:** `backend/app/modules/gear/router.py`

Dodaj walidację w endpointach `create_container` i `create_item`:

```python
# Before creating container
limits_service = LimitsService()
containers_count = await gear_repo.count_user_containers(current_user.id)
if not await limits_service.check_container_limit(current_user, containers_count):
    raise HTTPException(
        status_code=403,
        detail="Container limit reached. Upgrade to premium for more containers."
    )

# Before creating item
items_count = await gear_repo.count_user_items(current_user.id)
if not await limits_service.check_item_limit(current_user, items_count):
    raise HTTPException(
        status_code=403,
        detail="Item limit reached. Upgrade to premium for more items."
    )
```

---

### Phase 3: Frontend - Types & API

#### Step 3.1: TypeScript types

**File:** `src/modules/gear/types/limits.types.ts`

```typescript
export interface IUserLimits {
  tier: 'free' | 'premium'
  limits: {
    items: number
    containers: number
  }
  usage: {
    items: number
    containers: number
  }
  percentage: {
    items: number
    containers: number
  }
}
```

#### Step 3.2: API service

**File:** `src/modules/gear/services/limitsApiService.ts`

```typescript
import { apiClient } from '@/shared/services/apiClient'
import type { IUserLimits } from '../types/limits.types'

export const limitsApiService = {
  async getUserLimits(): Promise<IUserLimits> {
    const response = await apiClient.get<IUserLimits>('/gear/me/limits')
    return response.data
  },
}
```

---

### Phase 4: Frontend - UI Components

#### Step 4.1: Komponent wyświetlania limitów

**File:** `src/modules/gear/components/AccountLimitsCard.vue`

```vue
<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { limitsApiService } from '../services/limitsApiService'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const { data: limits, isLoading } = useQuery({
  queryKey: ['user-limits'],
  queryFn: () => limitsApiService.getUserLimits(),
})

const getProgressColor = (percentage: number): string => {
  if (percentage >= 90) return 'destructive'
  if (percentage >= 75) return 'warning'
  return 'default'
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>
        {{ t('gear.settings.accountLimits.title') }}
        <Badge :variant="limits?.tier === 'premium' ? 'default' : 'secondary'">
          {{ limits?.tier === 'premium' ? t('gear.settings.accountLimits.premium') : t('gear.settings.accountLimits.free') }}
        </Badge>
      </CardTitle>
    </CardHeader>
    <CardContent v-if="limits && !isLoading">
      <!-- Items limit -->
      <div class="space-y-2">
        <div class="flex justify-between text-sm">
          <span>{{ t('gear.settings.accountLimits.items') }}</span>
          <span>{{ limits.usage.items }} / {{ limits.limits.items }}</span>
        </div>
        <Progress :model-value="limits.percentage.items" :class="getProgressColor(limits.percentage.items)" />
      </div>
      
      <!-- Containers limit -->
      <div class="space-y-2 mt-4">
        <div class="flex justify-between text-sm">
          <span>{{ t('gear.settings.accountLimits.containers') }}</span>
          <span>{{ limits.usage.containers }} / {{ limits.limits.containers }}</span>
        </div>
        <Progress :model-value="limits.percentage.containers" :class="getProgressColor(limits.percentage.containers)" />
      </div>
      
      <!-- Upgrade prompt if near limit -->
      <div v-if="limits.percentage.items >= 80 || limits.percentage.containers >= 80" class="mt-4 p-3 bg-muted rounded-md">
        <p class="text-sm">{{ t('gear.settings.accountLimits.upgradePrompt') }}</p>
      </div>
    </CardContent>
  </Card>
</template>
```

#### Step 4.2: Dodanie do Gear Settings

**File:** `src/modules/gear/pages/GearSettingsPage.vue`

Dodaj `AccountLimitsCard` do strony ustawień.

---

### Phase 5: Error Handling & User Feedback

#### Step 5.1: Obsługa błędów limitów

**File:** `src/modules/gear/composables/useGear.ts`

Dodaj obsługę błędów 403 przy tworzeniu przedmiotów/kontenerów:

```typescript
try {
  await createItem(...)
} catch (error) {
  if (error.response?.status === 403 && error.response?.data?.detail?.includes('limit')) {
    toast.error(t('gear.errors.limitReached'))
    // Optionally redirect to settings or show upgrade dialog
  }
}
```

---

## 🎨 UI/UX Considerations

- **Progress bars** - wizualne przedstawienie wykorzystania limitów
- **Color coding** - czerwony przy >90%, żółty przy >75%
- **Upgrade prompts** - zachęta do upgrade przy zbliżaniu się do limitu
- **Clear messaging** - jasne komunikaty o limitach i możliwościach upgrade

---

## 🔄 Future Enhancements

### Opcja: Monitoring przestrzeni DB

Jeśli zdecydujemy się na limity zależne od wykorzystanej przestrzeni DB:

1. **Backend:**
   - Funkcja obliczająca rozmiar danych użytkownika w DB
   - Endpoint `GET /me/storage-usage` zwracający wykorzystaną przestrzeń
   - Konfiguracja limitów w MB/GB zamiast liczby przedmiotów

2. **Frontend:**
   - Wyświetlanie wykorzystanej przestrzeni zamiast liczby przedmiotów
   - Progress bar pokazujący wykorzystanie przestrzeni

---

## 📊 Testing

### Backend Tests

- Test sprawdzania limitów dla kont free/premium
- Test walidacji limitów przy tworzeniu przedmiotów/kontenerów
- Test endpointu `/me/limits`
- Test błędów przy przekroczeniu limitów

### Frontend Tests

- Test wyświetlania limitów w UI
- Test progress bars
- Test komunikatów błędów przy limitach
- Test upgrade prompts

---

## 📝 Notes

- Limity mogą być konfigurowane przez zmienne środowiskowe
- Domyślne wartości: free (500/10), premium (1000/50)
- Możliwość rozszerzenia o więcej tierów w przyszłości
- Opcjonalnie: limity mogą być dynamiczne (zależne od wykorzystanej przestrzeni DB)
