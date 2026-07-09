# FEATURE-026: Refaktoryzacja systemu query parametrów (`returnTo` i `from`)

**Status:** 🔄 Planned  
**Priority:** High  
**Complexity:** Medium  
**Related:** [ROADMAP_OFFLINE.md](../ROADMAP_OFFLINE.md#-refaktoryzacja-systemu-query-parametrów-returnto-i-from), [2026-07-09--query-params-analysis.md](../reviews/2026-07-09--query-params-analysis.md)

## 📋 Opis

Refaktoryzacja systemu zarządzania query parametrami `returnTo` i `from` w module gear, aby zapewnić type safety, centralizację logiki i spójność w całej aplikacji.

## 🎯 Cele

1. **Type Safety** - Typowanie wartości query parametrów z autocompletion w IDE
2. **Centralizacja** - Jedna lokalizacja dla logiki nawigacji i zarządzania parametrami
3. **Spójność** - Ujednolicone użycie funkcji z `routes.ts` zamiast hardcoded stringów
4. **Czystość** - Automatyczne czyszczenie parametrów z URL po użyciu
5. **Utrzymywalność** - Mniej duplikacji kodu, łatwiejsze dodawanie nowych wartości

## 🔍 Obecny stan

### Parametr `returnTo`

**Cel:** Określa, dokąd wrócić po wykonaniu akcji (zapis/anulowanie) w formularzach.

**Możliwe wartości:**
- `'detail'` - powrót do strony szczegółów przedmiotu (`ItemDetailPage`)
- `'shopping'` - powrót do planowania zakupów (`ShoppingPlanningPage`)
- `'container'` - powrót do szczegółów kontenera (`ContainerDetailPage`)
- `undefined` - domyślnie powrót do kontenera

**Miejsca użycia:**
- `ItemFormPage` - obsługa powrotu po zapisie/anulowaniu
- `ItemDetailPage` - przekazywanie przy edycji przedmiotu
- `ContainerDetailPage` - przekazywanie przy edycji przedmiotu z listy
- `ShoppingPlanningPage` - obsługa powrotu z edycji
- `ShoppingListItem.vue` - **hardcoded string** w URL (linia 49)
- `AvailableItemCard.vue` - **hardcoded string** w URL (linia 57)

### Parametr `from`

**Cel:** Określa źródło nawigacji do `ItemDetailPage`, używane do kontekstowego przycisku "Wstecz".

**Możliwe wartości:**
- `'all-items'` - nawigacja z `AllItemsPage`
- `'container'` - nawigacja z `ContainerDetailPage` (przez `ItemsTable` lub `ContainerItemImageCard`)

**Miejsca użycia:**
- `AllItemsPage` - przekazywanie `from=all-items`
- `ItemsTable` - przekazywanie `from=container`
- `ContainerItemImageCard` - przekazywanie `from=container`
- `ItemDetailPage` - określa cel przycisku wstecz
- `ItemFormPage` - zachowanie przy powrocie do `ItemDetailPage`

## ❌ Zidentyfikowane problemy

### 1. Niespójność w przekazywaniu parametrów

**Problem:** W niektórych miejscach używane są hardcoded stringi zamiast funkcji z `routes.ts`.

**Przykłady:**
```vue
<!-- ShoppingListItem.vue, AvailableItemCard.vue -->
<RouterLink :to="`${GearRoutePath.ItemEditById(item._containerId, item.id)}?returnTo=shopping`" />
```

**Wpływ:**
- Brak type safety
- Trudność w refaktoryzacji ścieżek
- Ryzyko błędów w URL

### 2. Brak typowania

**Problem:** Wartości query parametrów są stringami bez walidacji.

**Obecny kod:**
```typescript
const returnTo = route.query.returnTo as string | undefined
const from = route.query.from as string | undefined
```

**Wpływ:**
- Brak autocompletion w IDE
- Możliwość przekazania nieprawidłowych wartości
- Brak walidacji w czasie kompilacji

### 3. Rozproszona logika

**Problem:** Obsługa query parametrów jest rozproszona po wielu plikach.

**Miejsca z logiką:**
- `ItemFormPage.vue` - obsługa `returnTo` i `from` w `onSubmit` (linie 195-214) i `handleCancel` (linie 240-253)
- `ItemDetailPage.vue` - obsługa `from` w `backTo` computed
- `ItemHeader.vue` - obsługa `from` w `handleEdit` (linie 38-46) i `backTo` (linie 31-36)
- `ShoppingPlanningPage.vue` - obsługa `returnTo` w `onMounted` (linie 538-543)
- `ContainerDetailPage.vue` - przekazywanie `returnTo: 'container'` (linia 113)

**Wpływ:**
- Trudność w utrzymaniu
- Duplikacja kodu
- Ryzyko niespójności

### 4. Brak automatycznego czyszczenia parametrów

**Problem:** Query parametry pozostają w URL po użyciu (z wyjątkiem `ShoppingPlanningPage`).

**Obecny stan:**
- `ShoppingPlanningPage` - czyści parametry: `router.replace({ query: {} })` (linia 542)
- Inne strony - parametry pozostają w URL

**Wpływ:**
- Brudne URL-e w historii przeglądarki
- Możliwość nieoczekiwanych zachowań przy odświeżeniu strony

### 5. Ręczne zarządzanie parametrami

**Problem:** Warunki sprawdzające wartości parametrów są powtarzane w wielu miejscach.

**Przykład duplikacji w `ItemFormPage.vue`:**
```typescript
// onSubmit (linie 202-214)
if (returnTo === 'detail') {
  // ...
} else if (returnTo === 'shopping') {
  // ...
} else {
  // Default: return to container
}

// handleCancel (linie 241-253)
if (returnTo === 'detail' && itemId) {
  // ...
} else if (returnTo === 'shopping') {
  // ...
} else {
  // Default: return to container
}
```

## ✅ Plan implementacji

### Faza 1: Stworzenie typów i helper functions (Wysoki priorytet)

**Plik:** `src/modules/gear/utils/navigationParams.ts`

**Zadania:**

1. **Utworzenie typów:**
   ```typescript
   export type ReturnToValue = 'detail' | 'shopping' | 'container'
   export type FromValue = 'all-items' | 'container'
   ```

2. **Utworzenie stałych z dozwolonymi wartościami:**
   ```typescript
   export const RETURN_TO_VALUES: readonly ReturnToValue[] = [
     'detail',
     'shopping',
     'container',
   ] as const

   export const FROM_VALUES: readonly FromValue[] = [
     'all-items',
     'container',
   ] as const
   ```

3. **Funkcje walidacji:**
   ```typescript
   export function isValidReturnTo(value: unknown): value is ReturnToValue {
     return typeof value === 'string' && RETURN_TO_VALUES.includes(value as ReturnToValue)
   }

   export function isValidFrom(value: unknown): value is FromValue {
     return typeof value === 'string' && FROM_VALUES.includes(value as FromValue)
   }
   ```

4. **Interface dla query parametrów:**
   ```typescript
   export interface NavigationQuery {
     returnTo?: ReturnToValue
     from?: FromValue
   }
   ```

5. **Helper function do tworzenia query:**
   ```typescript
   export function createNavigationQuery(
     returnTo?: ReturnToValue,
     from?: FromValue,
   ): NavigationQuery {
     return {
       ...(returnTo && { returnTo }),
       ...(from && { from }),
     }
   }
   ```

6. **Helper functions do odczytu z route:**
   ```typescript
   import type { Route } from 'vue-router'

   export function getReturnTo(route: Route): ReturnToValue | undefined {
     const value = route.query.returnTo
     return isValidReturnTo(value) ? value : undefined
   }

   export function getFrom(route: Route): FromValue | undefined {
     const value = route.query.from
     return isValidFrom(value) ? value : undefined
   }
   ```

7. **Helper function do tworzenia ścieżki edycji przedmiotu:**
   ```typescript
   import type { RouteLocationRaw } from 'vue-router'
   import { GearRoutePath } from '../routes'

   export function createItemEditPath(
     containerId: string,
     itemId: string,
     returnTo?: ReturnToValue,
     from?: FromValue,
   ): RouteLocationRaw {
     return {
       path: GearRoutePath.ItemEditById(containerId, itemId),
       query: createNavigationQuery(returnTo, from),
     }
   }
   ```

**Kryteria akceptacji:**
- ✅ Plik `navigationParams.ts` utworzony z wszystkimi typami i funkcjami
- ✅ Wszystkie funkcje mają odpowiednie typy TypeScript
- ✅ Funkcje walidacji poprawnie sprawdzają wartości
- ✅ Testy jednostkowe dla funkcji walidacji (opcjonalnie)

**Szacowany czas:** 1-2 godziny

---

### Faza 2: Zastąpienie hardcoded stringów (Wysoki priorytet)

**Pliki do modyfikacji:**
- `src/modules/gear/components/shopping/ShoppingListItem.vue`
- `src/modules/gear/components/shopping/AvailableItemCard.vue`

**Zadania:**

1. **ShoppingListItem.vue (linia 49):**
   ```vue
   <!-- Przed -->
   <RouterLink
     :to="`${GearRoutePath.ItemEditById(item._containerId, item.id)}?returnTo=shopping`"
     class="font-medium hover:text-primary hover:underline transition-colors"
   >
     {{ item.name }}
   </RouterLink>

   <!-- Po -->
   <RouterLink
     :to="createItemEditPath(item._containerId, item.id, 'shopping')"
     class="font-medium hover:text-primary hover:underline transition-colors"
   >
     {{ item.name }}
   </RouterLink>
   ```

   **Zmiany:**
   - Import `createItemEditPath` z `@/modules/gear/utils/navigationParams`
   - Zastąpienie template stringa funkcją `createItemEditPath`

2. **AvailableItemCard.vue (linia 57):**
   ```vue
   <!-- Przed -->
   <RouterLink
     :to="`${GearRoutePath.ItemEditById(item._containerId, item.id)}?returnTo=shopping`"
     class="font-medium hover:text-primary hover:underline transition-colors"
   >
     {{ item.name }}
   </RouterLink>

   <!-- Po -->
   <RouterLink
     :to="createItemEditPath(item._containerId, item.id, 'shopping')"
     class="font-medium hover:text-primary hover:underline transition-colors"
   >
     {{ item.name }}
   </RouterLink>
   ```

   **Zmiany:**
   - Import `createItemEditPath` z `@/modules/gear/utils/navigationParams`
   - Zastąpienie template stringa funkcją `createItemEditPath`

**Kryteria akceptacji:**
- ✅ Brak hardcoded stringów w URL
- ✅ Użycie funkcji `createItemEditPath` zamiast template stringów
- ✅ Działanie nawigacji niezmienione
- ✅ Type safety zapewnione przez TypeScript

**Szacowany czas:** 30 minut

---

### Faza 3: Refaktoryzacja `ItemFormPage` do użycia helper functions (Wysoki priorytet)

**Plik:** `src/modules/gear/pages/ItemFormPage.vue`

**Zadania:**

1. **Import helper functions:**
   ```typescript
   import { getReturnTo, getFrom, createNavigationQuery } from '../utils/navigationParams'
   ```

2. **Zastąpienie odczytu parametrów w `onSubmit` (linie 195-214):**
   ```typescript
   // Przed
   const returnTo = route.query.returnTo as string | undefined

   // Po
   const returnTo = getReturnTo(route)
   const from = getFrom(route)
   ```

3. **Uproszczenie logiki nawigacji w `onSubmit`:**
   ```typescript
   // Przed (linie 201-214)
   if (returnTo === 'detail') {
     const from = route.query.from as string | undefined
     router.push({
       path: GearRoutePath.ItemDetailById(containerId, itemId),
       ...(from && { query: { from } }),
     })
   } else if (returnTo === 'shopping') {
     router.push(GearRoutePath.ShoppingPlanning)
   } else {
     router.push(GearRoutePath.ContainerDetailById(containerId))
   }

   // Po
   if (returnTo === 'detail' && itemId) {
     router.push({
       path: GearRoutePath.ItemDetailById(containerId, itemId),
       query: createNavigationQuery(undefined, from),
     })
   } else if (returnTo === 'shopping') {
     router.push(GearRoutePath.ShoppingPlanning)
   } else {
     router.push(GearRoutePath.ContainerDetailById(containerId))
   }
   ```

4. **Zastąpienie odczytu parametrów w `handleCancel` (linie 240-253):**
   ```typescript
   // Przed
   const returnTo = route.query.returnTo as string | undefined
   if (returnTo === 'detail' && itemId) {
     const from = route.query.from as string | undefined
     router.push({
       path: GearRoutePath.ItemDetailById(containerId, itemId),
       ...(from && { query: { from } }),
     })
   } else if (returnTo === 'shopping') {
     router.push(GearRoutePath.ShoppingPlanning)
   } else {
     router.push(GearRoutePath.ContainerDetailById(containerId))
   }

   // Po
   const returnTo = getReturnTo(route)
   const from = getFrom(route)
   
   if (returnTo === 'detail' && itemId) {
     router.push({
       path: GearRoutePath.ItemDetailById(containerId, itemId),
       query: createNavigationQuery(undefined, from),
     })
   } else if (returnTo === 'shopping') {
     router.push(GearRoutePath.ShoppingPlanning)
   } else {
     router.push(GearRoutePath.ContainerDetailById(containerId))
   }
   ```

**Kryteria akceptacji:**
- ✅ Użycie `getReturnTo()` i `getFrom()` zamiast bezpośredniego odczytu z `route.query`
- ✅ Użycie `createNavigationQuery()` do tworzenia query parametrów
- ✅ Działanie nawigacji niezmienione
- ✅ Type safety zapewnione

**Szacowany czas:** 1 godzina

---

### Faza 4: Stworzenie composable `useNavigationReturn` (Średni priorytet)

**Plik:** `src/modules/gear/composables/useNavigationReturn.ts`

**Zadania:**

1. **Utworzenie composable:**
   ```typescript
   import { computed } from 'vue'
   import { useRoute, useRouter } from 'vue-router'
   import { GearRoutePath } from '../routes'
   import { getReturnTo, getFrom, createNavigationQuery, type ReturnToValue, type FromValue } from '../utils/navigationParams'

   export function useNavigationReturn(containerId: string, itemId?: string) {
     const route = useRoute()
     const router = useRouter()

     const returnTo = computed(() => getReturnTo(route))
     const from = computed(() => getFrom(route))

     function navigateBack() {
       const returnToValue = returnTo.value
       const fromValue = from.value

       if (returnToValue === 'detail' && itemId) {
         router.push({
           path: GearRoutePath.ItemDetailById(containerId, itemId),
           query: createNavigationQuery(undefined, fromValue),
         })
       } else if (returnToValue === 'shopping') {
         router.push(GearRoutePath.ShoppingPlanning)
       } else {
         router.push(GearRoutePath.ContainerDetailById(containerId))
       }
     }

     function navigateBackAndClean() {
       navigateBack()
       // Clean query params from URL after navigation
       router.replace({ query: {} })
     }

     return {
       returnTo,
       from,
       navigateBack,
       navigateBackAndClean,
     }
   }
   ```

2. **Refaktoryzacja `ItemFormPage.vue` do użycia composable:**
   ```typescript
   // Import
   import { useNavigationReturn } from '../composables/useNavigationReturn'

   // W setup
   const { navigateBack } = useNavigationReturn(containerId, itemId)

   // W onSubmit (zamiast całej logiki if/else)
   if (isEditMode && itemId) {
     await updateItem(itemId, data as IUpdateItemDto)
     toast.success(t('common.success'))
     navigateBack()
   } else {
     // ... create logic
     navigateBack()
   }

   // W handleCancel
   const handleCancel = () => {
     navigateBack()
   }
   ```

**Kryteria akceptacji:**
- ✅ Composable `useNavigationReturn` utworzony
- ✅ `ItemFormPage` używa composable zamiast duplikowanej logiki
- ✅ Działanie nawigacji niezmienione
- ✅ Kod jest bardziej czytelny i łatwiejszy w utrzymaniu

**Szacowany czas:** 1-2 godziny

---

### Faza 5: Refaktoryzacja innych komponentów (Średni priorytet)

**Pliki do modyfikacji:**
- `src/modules/gear/components/ItemHeader.vue`
- `src/modules/gear/pages/ItemDetailPage.vue`
- `src/modules/gear/pages/ContainerDetailPage.vue`
- `src/modules/gear/pages/ShoppingPlanningPage.vue`

**Zadania:**

1. **ItemHeader.vue:**
   - Zastąpienie `route.query.from as string | undefined` przez `getFrom(route)`
   - Użycie `createNavigationQuery()` w `handleEdit` (linie 38-46)
   - Użycie `getFrom()` w `backTo` computed (linie 31-36)

2. **ItemDetailPage.vue:**
   - Sprawdzenie, czy używa `ItemHeader` (jeśli tak, zmiany w `ItemHeader` wystarczą)
   - Jeśli nie, zastosować podobne zmiany jak w `ItemHeader`

3. **ContainerDetailPage.vue:**
   - Użycie `createNavigationQuery('container')` w `handleEditItem` (linia 113)

4. **ShoppingPlanningPage.vue:**
   - Zastąpienie `route.query.returnTo as string | undefined` przez `getReturnTo(route)` w `onMounted` (linie 538-543)

**Kryteria akceptacji:**
- ✅ Wszystkie komponenty używają helper functions zamiast bezpośredniego odczytu z `route.query`
- ✅ Spójność w całej aplikacji
- ✅ Działanie nawigacji niezmienione

**Szacowany czas:** 1-2 godziny

---

### Faza 6: Automatyczne czyszczenie parametrów (Średni priorytet)

**Zadania:**

1. **Rozszerzenie composable `useNavigationReturn`:**
   - Dodać funkcję `navigateBackAndClean()` (już dodana w Fazie 4)
   - Opcjonalnie: automatyczne czyszczenie po nawigacji

2. **Aktualizacja `ItemFormPage.vue`:**
   - Użycie `navigateBackAndClean()` zamiast `navigateBack()` po zapisie/anulowaniu

3. **Aktualizacja `ShoppingPlanningPage.vue`:**
   - Sprawdzenie, czy logika czyszczenia w `onMounted` jest nadal potrzebna
   - Jeśli używa composable, usunąć ręczne czyszczenie

**Alternatywne podejście - router guard:**

Jeśli automatyczne czyszczenie ma być bardziej globalne, można rozważyć router guard:

```typescript
// W router guard lub composable
watch(() => route.query.returnTo, (returnTo) => {
  if (returnTo && route.name === 'gear-item-edit') {
    // Parametr został użyty, można go wyczyścić po nawigacji
  }
})
```

**Kryteria akceptacji:**
- ✅ Query parametry są czyszczone z URL po użyciu
- ✅ Historia przeglądarki zawiera czyste URL-e
- ✅ Brak nieoczekiwanych zachowań przy odświeżeniu strony

**Szacowany czas:** 1 godzina

---

### Faza 7: Testy i weryfikacja (Wysoki priorytet)

**Zadania:**

1. **Testy manualne:**
   - ✅ Nawigacja z `ShoppingListItem` do edycji i powrót
   - ✅ Nawigacja z `AvailableItemCard` do edycji i powrót
   - ✅ Nawigacja z `ItemDetailPage` do edycji i powrót
   - ✅ Nawigacja z `ContainerDetailPage` do edycji i powrót
   - ✅ Nawigacja z `AllItemsPage` do `ItemDetailPage` i wstecz
   - ✅ Anulowanie edycji z różnych miejsc
   - ✅ Zapis edycji z różnych miejsc
   - ✅ Sprawdzenie, czy query parametry są czyszczone z URL

2. **Testy automatyczne (opcjonalnie):**
   - Testy jednostkowe dla funkcji walidacji
   - Testy dla composable `useNavigationReturn`
   - E2E testy dla przepływów nawigacji

3. **Weryfikacja TypeScript:**
   - ✅ Brak błędów kompilacji
   - ✅ Wszystkie typy są poprawne
   - ✅ Autocompletion działa w IDE

**Kryteria akceptacji:**
- ✅ Wszystkie testy manualne przechodzą
- ✅ Brak błędów TypeScript
- ✅ Kod jest zgodny z konwencjami projektu (ESLint)

**Szacowany czas:** 1-2 godziny

---

## 📊 Podsumowanie faz

| Faza | Priorytet | Szacowany czas | Status |
|------|-----------|----------------|--------|
| 1. Typy i helper functions | Wysoki | 1-2h | ⏳ Pending |
| 2. Zastąpienie hardcoded stringów | Wysoki | 30min | ⏳ Pending |
| 3. Refaktoryzacja ItemFormPage | Wysoki | 1h | ⏳ Pending |
| 4. Composable useNavigationReturn | Średni | 1-2h | ⏳ Pending |
| 5. Refaktoryzacja innych komponentów | Średni | 1-2h | ⏳ Pending |
| 6. Automatyczne czyszczenie | Średni | 1h | ⏳ Pending |
| 7. Testy i weryfikacja | Wysoki | 1-2h | ⏳ Pending |
| **RAZEM** | | **6-10h** | |

## 🎯 Korzyści po implementacji

1. **Type Safety:**
   - ✅ Autocompletion w IDE dla wartości `returnTo` i `from`
   - ✅ Walidacja wartości w czasie kompilacji
   - ✅ Brak możliwości przekazania nieprawidłowych wartości

2. **Spójność:**
   - ✅ Wszystkie komponenty używają tych samych helper functions
   - ✅ Brak hardcoded stringów w URL
   - ✅ Łatwość refaktoryzacji ścieżek

3. **Utrzymywalność:**
   - ✅ Centralizacja logiki nawigacji
   - ✅ Mniej duplikacji kodu
   - ✅ Łatwiejsze dodawanie nowych wartości parametrów

4. **Czystość:**
   - ✅ Czyste URL-e w historii przeglądarki
   - ✅ Brak nieoczekiwanych zachowań przy odświeżeniu strony

## 🔄 Migracja istniejącego kodu

### Przykład migracji dla `ShoppingListItem.vue`:

```vue
<script setup lang="ts">
// Przed
import { GearRoutePath } from '../../routes'

// Po
import { createItemEditPath } from '../../utils/navigationParams'
</script>

<template>
  <!-- Przed -->
  <RouterLink
    :to="`${GearRoutePath.ItemEditById(item._containerId, item.id)}?returnTo=shopping`"
  >
    {{ item.name }}
  </RouterLink>

  <!-- Po -->
  <RouterLink :to="createItemEditPath(item._containerId, item.id, 'shopping')">
    {{ item.name }}
  </RouterLink>
</template>
```

### Przykład migracji dla `ItemFormPage.vue`:

```typescript
// Przed
const returnTo = route.query.returnTo as string | undefined
const from = route.query.from as string | undefined

if (returnTo === 'detail') {
  router.push({
    path: GearRoutePath.ItemDetailById(containerId, itemId),
    ...(from && { query: { from } }),
  })
}

// Po
import { useNavigationReturn } from '../composables/useNavigationReturn'

const { navigateBack } = useNavigationReturn(containerId, itemId)

// W onSubmit lub handleCancel
navigateBack()
```

## 📝 Uwagi implementacyjne

1. **Zachowanie kompatybilności wstecznej:**
   - Istniejące URL-e z query parametrami powinny nadal działać
   - Funkcje walidacji powinny zwracać `undefined` dla nieprawidłowych wartości zamiast rzucać błędy

2. **Obsługa edge cases:**
   - Co się dzieje, gdy `returnTo` ma nieprawidłową wartość? → Fallback do kontenera
   - Co się dzieje, gdy `from` ma nieprawidłową wartość? → Ignorowanie parametru

3. **Rozszerzalność:**
   - Jeśli w przyszłości będą potrzebne nowe wartości `returnTo` lub `from`, wystarczy dodać je do typów i stałych w `navigationParams.ts`

4. **Testowanie:**
   - Szczególnie ważne jest przetestowanie wszystkich przepływów nawigacji
   - Sprawdzenie, czy query parametry są poprawnie przekazywane i czyszczone

## 🔗 Powiązane dokumenty

- [ROADMAP_OFFLINE.md](../ROADMAP_OFFLINE.md#-refaktoryzacja-systemu-query-parametrów-returnto-i-from)
- [2026-07-09--query-params-analysis.md](../reviews/2026-07-09--query-params-analysis.md)
- [routes.ts](../../src/modules/gear/routes.ts)

## 📌 Checklist implementacji

- [ ] Faza 1: Utworzenie `navigationParams.ts` z typami i helper functions
- [ ] Faza 2: Zastąpienie hardcoded stringów w `ShoppingListItem` i `AvailableItemCard`
- [ ] Faza 3: Refaktoryzacja `ItemFormPage` do użycia helper functions
- [ ] Faza 4: Stworzenie composable `useNavigationReturn`
- [ ] Faza 5: Refaktoryzacja innych komponentów (`ItemHeader`, `ItemDetailPage`, `ContainerDetailPage`, `ShoppingPlanningPage`)
- [ ] Faza 6: Implementacja automatycznego czyszczenia parametrów
- [ ] Faza 7: Testy manualne i weryfikacja
- [ ] Code review
- [ ] Aktualizacja dokumentacji (jeśli potrzebna)

