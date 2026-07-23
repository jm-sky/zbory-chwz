# Analiza użycia query parametrów `returnTo` i `from`

## Wprowadzenie

Dokument analizuje użycie query parametrów `returnTo` i `from` w module gear aplikacji, identyfikuje problemy i proponuje ulepszenia.

## Obecny stan

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
- `ShoppingListItem` - **hardcoded string** w URL
- `AvailableItemCard` - **hardcoded string** w URL

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

## Zidentyfikowane problemy

### 1. Niespójność w przekazywaniu parametrów

**Problem:** W niektórych miejscach używane są hardcoded stringi zamiast funkcji z `routes.ts`.

**Przykłady:**
```vue
<!-- ShoppingListItem.vue, AvailableItemCard.vue -->
<RouterLink :to="`/gear/${item._containerId}/items/${item.id}/edit?returnTo=shopping`" />
```

**Powinno być:**
```vue
<RouterLink :to="{ 
  path: GearRoutePath.ItemEditById(item._containerId, item.id),
  query: { returnTo: 'shopping' }
}" />
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
- `ItemFormPage` - obsługa `returnTo` i `from` w `onSubmit` i `handleCancel`
- `ItemDetailPage` - obsługa `from` w `backTo` computed
- `ShoppingPlanningPage` - obsługa `returnTo` w `onMounted`
- Różne komponenty przekazujące parametry

**Wpływ:**
- Trudność w utrzymaniu
- Duplikacja kodu
- Ryzyko niespójności

### 4. Niejednoznaczność semantyczna

**Problem:** `returnTo` i `from` mają różne znaczenia, ale są często używane razem.

- `returnTo` = dokąd wrócić **po akcji** (zapis/anulowanie)
- `from` = skąd przyszliśmy (dla nawigacji wstecz)

**Przykład:**
```typescript
// ItemDetailPage -> ItemFormPage
query: {
  returnTo: 'detail',  // wróć do detail po zapisie
  from: 'all-items'    // skąd przyszliśmy (dla przycisku wstecz w detail)
}
```

**Wpływ:**
- Możliwość pomyłki w użyciu
- Trudność w zrozumieniu przepływu

### 5. Brak automatycznego czyszczenia parametrów

**Problem:** Query parametry pozostają w URL po użyciu (z wyjątkiem `ShoppingPlanningPage`).

**Obecny stan:**
- `ShoppingPlanningPage` - czyści parametry: `router.replace({ query: {} })`
- Inne strony - parametry pozostają w URL

**Wpływ:**
- Brudne URL-e w historii przeglądarki
- Możliwość nieoczekiwanych zachowań przy odświeżeniu strony

### 6. Ręczne zarządzanie parametrami

**Problem:** Warunki sprawdzające wartości parametrów są powtarzane w wielu miejscach.

**Przykład duplikacji:**
```typescript
// ItemFormPage - onSubmit
if (returnTo === 'detail') {
  // ...
} else if (returnTo === 'shopping') {
  // ...
} else {
  // Default: return to container
}

// ItemFormPage - handleCancel
if (returnTo === 'detail' && itemId) {
  // ...
} else if (returnTo === 'shopping') {
  // ...
} else {
  // Default: return to container
}
```

**Wpływ:**
- Duplikacja kodu
- Trudność w dodaniu nowych wartości
- Ryzyko niespójności

## Proponowane ulepszenia

### 1. Stworzenie typów i enumów

**Lokalizacja:** `src/modules/gear/utils/navigationParams.ts`

```typescript
export type ReturnToValue = 'detail' | 'shopping' | 'container'
export type FromValue = 'all-items' | 'container'

export const RETURN_TO_VALUES: readonly ReturnToValue[] = [
  'detail',
  'shopping',
  'container',
] as const

export const FROM_VALUES: readonly FromValue[] = [
  'all-items',
  'container',
] as const

export function isValidReturnTo(value: unknown): value is ReturnToValue {
  return typeof value === 'string' && RETURN_TO_VALUES.includes(value as ReturnToValue)
}

export function isValidFrom(value: unknown): value is FromValue {
  return typeof value === 'string' && FROM_VALUES.includes(value as FromValue)
}
```

**Korzyści:**
- Type safety
- Autocompletion w IDE
- Walidacja wartości

### 2. Helper functions do zarządzania query parametrami

**Lokalizacja:** `src/modules/gear/utils/navigationParams.ts`

```typescript
import type { RouteLocationRaw } from 'vue-router'
import type { Route } from 'vue-router'
import { GearRoutePath } from '../routes'
import type { FromValue, ReturnToValue } from './navigationParams'

export interface NavigationQuery {
  returnTo?: ReturnToValue
  from?: FromValue
}

export function createNavigationQuery(
  returnTo?: ReturnToValue,
  from?: FromValue,
): NavigationQuery {
  return {
    ...(returnTo && { returnTo }),
    ...(from && { from }),
  }
}

export function getReturnTo(route: Route): ReturnToValue | undefined {
  const value = route.query.returnTo
  return isValidReturnTo(value) ? value : undefined
}

export function getFrom(route: Route): FromValue | undefined {
  const value = route.query.from
  return isValidFrom(value) ? value : undefined
}

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

**Korzyści:**
- Centralizacja logiki
- Łatwość użycia
- Spójność w całej aplikacji

### 3. Ujednolicenie użycia `routes.ts`

**Zmiana w `ShoppingListItem.vue` i `AvailableItemCard.vue`:**

```vue
<!-- Przed -->
<RouterLink :to="`/gear/${item._containerId}/items/${item.id}/edit?returnTo=shopping`" />

<!-- Po -->
<RouterLink :to="createItemEditPath(item._containerId, item.id, 'shopping')" />
```

**Korzyści:**
- Użycie funkcji z `routes.ts`
- Type safety
- Łatwość refaktoryzacji

### 4. Centralizacja logiki nawigacji

**Lokalizacja:** `src/modules/gear/composables/useNavigationReturn.ts`

```typescript
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { GearRoutePath } from '../routes'
import { getReturnTo, getFrom, type ReturnToValue } from '../utils/navigationParams'

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
        ...(fromValue && { query: { from: fromValue } }),
      })
    } else if (returnToValue === 'shopping') {
      router.push(GearRoutePath.ShoppingPlanning)
    } else {
      router.push(GearRoutePath.ContainerDetailById(containerId))
    }
  }

  return {
    returnTo,
    from,
    navigateBack,
  }
}
```

**Korzyści:**
- Reużywalna logika
- Mniej duplikacji
- Łatwiejsze testowanie

### 5. Automatyczne czyszczenie parametrów

**Dodanie do composable:**

```typescript
function navigateBackAndClean() {
  navigateBack()
  // Opcjonalnie: wyczyść parametry z URL
  router.replace({ query: {} })
}
```

**Lub w guardach/obserwatorach:**

```typescript
// W ShoppingPlanningPage
watch(() => route.query.returnTo, (returnTo) => {
  if (returnTo === 'shopping') {
    // Po obsłużeniu, wyczyść parametry
    router.replace({ query: {} })
  }
})
```

**Korzyści:**
- Czyste URL-e
- Brak nieoczekiwanych zachowań

### 6. Rozważenie połączenia `returnTo` i `from`

**Opcja A:** Automatyczne zachowanie `from` gdy `returnTo='detail'`

```typescript
function createItemEditPath(
  containerId: string,
  itemId: string,
  returnTo: ReturnToValue,
  from?: FromValue, // opcjonalne, może być automatycznie zachowane
): RouteLocationRaw
```

**Opcja B:** Jeden parametr `context` zamiast dwóch

```typescript
type NavigationContext = 
  | { type: 'from-all-items' }
  | { type: 'from-container', containerId: string }
  | { type: 'from-shopping' }
```

**Korzyści:**
- Prostsza logika
- Mniej parametrów do zarządzania

## Priorytety implementacji

### Wysoki priorytet

1. **Zastąpienie hardcoded stringów funkcjami z `routes.ts`**
   - `ShoppingListItem.vue`
   - `AvailableItemCard.vue`
   - Wpływ: Bezpieczeństwo typów, łatwość refaktoryzacji

2. **Dodanie typów dla query parametrów**
   - Stworzenie `navigationParams.ts`
   - Wpływ: Type safety, autocompletion

3. **Helper functions do zarządzania parametrami**
   - `createNavigationQuery`, `getReturnTo`, `getFrom`
   - Wpływ: Centralizacja, spójność

### Średni priorytet

4. **Centralizacja logiki nawigacji (composables)**
   - `useNavigationReturn`
   - Wpływ: Mniej duplikacji, łatwiejsze utrzymanie

5. **Automatyczne czyszczenie parametrów**
   - Po obsłużeniu parametru
   - Wpływ: Czyste URL-e

### Niski priorytet

6. **Rozważenie połączenia `returnTo` i `from`**
   - Refaktoryzacja do jednego systemu
   - Wpływ: Uproszczenie logiki (wymaga większych zmian)

## Podsumowanie

System query parametrów `returnTo` i `from` działa, ale wymaga ujednolicenia i centralizacji. Główne problemy to:

- **Hardcoded stringi** zamiast funkcji z `routes.ts`
- **Brak typowania** wartości parametrów
- **Rozproszona logika** obsługi parametrów
- **Niejednoznaczność semantyczna** między `returnTo` i `from`
- **Brak automatycznego czyszczenia** parametrów po użyciu
- **Ręczne zarządzanie** parametrami w wielu miejscach

Wprowadzenie typów, helper functions i composables uprości utrzymanie i zmniejszy ryzyko błędów. Priorytetem powinno być zastąpienie hardcoded stringów i dodanie typowania.

## Przykładowy plan migracji

1. **Faza 1:** Stworzenie `navigationParams.ts` z typami i helper functions
2. **Faza 2:** Zastąpienie hardcoded stringów w `ShoppingListItem` i `AvailableItemCard`
3. **Faza 3:** Refaktoryzacja `ItemFormPage` do użycia helper functions
4. **Faza 4:** Stworzenie composable `useNavigationReturn`
5. **Faza 5:** Dodanie automatycznego czyszczenia parametrów
6. **Faza 6 (opcjonalnie):** Rozważenie połączenia `returnTo` i `from`

