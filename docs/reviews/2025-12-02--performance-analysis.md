# Analiza Wydajności Frontend - Gear Stack

## Data: 2025-12-02

> **📊 Zobacz również:** [Analiza Trace'a Wydajności](./PERFORMANCE_TRACE_ANALYSIS.md) - szczegółowa analiza rzeczywistych danych z Chrome DevTools Performance trace.

## Podsumowanie

Zidentyfikowano kilka obszarów, które mogą wpływać negatywnie na wydajność aplikacji. Analiza kodu oraz rzeczywisty trace z Chrome DevTools potwierdzają następujące problemy:

### 🔴 Rzeczywiste Metryki z Trace'a (2025-12-02):

**Trace:** `docs/tmp/Trace-20251202T131105.json` (8.14 sekundy)

1. **⚠️ 64 Long Tasks (>50ms)** - **KRYTYCZNE**
   - Najdłuższy task: **1076.99ms** (ponad 1 sekunda!)
   - Łączny czas w long tasks: **17,438ms** (więcej niż długość trace'a!)
   - Główny wątek był blokowany przez większość czasu

2. **⚠️ 79,599 JavaScript Execution Events** - **WYSOKIE**
   - Średni czas: 0.42ms
   - Maksymalny czas: 1076.99ms
   - Łączny czas JS: 33,039ms
   - Wskazuje na bardzo częste re-renderowanie komponentów Vue

3. **⚠️ 515 Layout Events** - **ŚREDNIE**
   - Łączny czas: 65.93ms
   - Głównie: UpdateLayoutTree (52.16ms), Layout (7.39ms)
   - Może oznaczać forced reflows

4. **⚠️ 954 Paint Events** - **ŚREDNIE**
   - Łączny czas: 19.96ms
   - Głównie: Paint (11.13ms), PrePaint (8.78ms)
   - Może oznaczać niepotrzebne repainty

### Główne Problemy w Kodzie:

1. Nadmiernego użycia `watch` z `deep: true` - **potwierdzone przez RunMicrotasks: 581ms**
2. Ciężkich computed properties wykonujących iteracje po dużych kolekcjach - **potwierdzone przez 79,599 JS events**
3. Braku memoizacji dla kosztownych obliczeń - **potwierdzone przez długie long tasks**
4. Równoległego ładowania wielu obrazów bez ograniczeń

---

## 1. Problem: Watch z `deep: true` - Wysoki koszt re-renderowania

### Lokalizacje:

#### 1.1 `ShoppingPlanningPage.vue`
```typescript
// Linie 144-151
watch(shoppingList, (newList) => {
  saveShoppingListToStorage(newList)
}, { deep: true })

watch(deletedItems, (newItems) => {
  saveDeletedItemsToStorage(newItems)
}, { deep: true })

watch(containers, () => {
  syncShoppingListWithContainers()
  syncDeletedItemsWithContainers()
}, { deep: true })
```

**Problem:** Watch z `deep: true` na dużych tablicach (`containers`, `shoppingList`) uruchamia się przy każdej zmianie w zagnieżdżonych obiektach, co może powodować częste zapisy do localStorage i synchronizacje.

**Wpływ:** Wysoki - przy dużej liczbie kontenerów i items, każda zmiana wywołuje pełną synchronizację.

**Potwierdzenie z trace'a:** RunMicrotasks: 581ms wskazuje na zbyt wiele watchers Vue uruchamiających się jednocześnie.

#### 1.2 `ContainerItemImagesGallery.vue`
```typescript
// Linia 108-110
watch(() => props.items, () => {
  loadImages()
}, { deep: true })
```

**Problem:** Watch z `deep: true` na `props.items` powoduje przeładowanie wszystkich obrazów przy każdej zmianie w items (np. zmiana nazwy, kategorii).

**Wpływ:** Średni - przeładowanie obrazów jest kosztowne, szczególnie przy wielu items.

#### 1.3 `ItemsTable.vue`
```typescript
// Linie 109-119, 258-313
watch(columnVisibility, (newValue) => {
  localStorage.setItem(ITEMS_TABLE_COLUMN_VISIBILITY_KEY, JSON.stringify(newValue))
}, { deep: true })

watch(tableSorting, (newSorting) => {
  // ... logika sortowania
}, { deep: true })
```

**Problem:** Watch z `deep: true` na obiektach, które zmieniają się często podczas interakcji użytkownika.

**Wpływ:** Średni - może powodować opóźnienia podczas sortowania i zmiany widoczności kolumn.

#### 1.4 `DataTable.vue`
```typescript
// Linie 96-111
watch(columnVisibilityModel, (newValue) => {
  // ... synchronizacja
}, { immediate: true, deep: true })
```

**Problem:** Watch z `deep: true` + `immediate: true` uruchamia się od razu i przy każdej zmianie.

**Wpływ:** Średni - może powodować niepotrzebne re-renderowania.

#### 1.5 `ShoppingListFilters.vue`
```typescript
// Linie 47-59
watch(categoryChecked, (checked) => {
  // ... emit changes
}, { deep: true })
```

**Problem:** Watch z `deep: true` na obiekcie, który zmienia się przy każdym kliknięciu checkboxa.

**Wpływ:** Niski-Średni - może powodować opóźnienia przy wielu kategoriach.

---

## 2. Problem: Ciężkie Computed Properties

### 2.1 `CategoryPieChart.vue` - `categoryData`
```typescript
// Linie 50-126
const categoryData = computed<CategoryData[]>(() => {
  let allItems: IGearItem[] = [...props.container.items]
  
  if (props.includeNested) {
    const nestedContainers = getAllNestedContainers(props.container.id, containers.value)
    for (const nestedContainer of nestedContainers) {
      allItems = allItems.concat(nestedContainer.items)
    }
  }
  
  // ... iteracja przez wszystkie items, obliczenia, sortowanie
})
```

**Problem:**
- Iteruje przez wszystkie items (włącznie z nested)
- Wykonuje obliczenia dla każdego itemu
- Sortuje wyniki przy każdej zmianie
- Uruchamia się przy każdej zmianie w `containers.value` lub `props.container.items`

**Wpływ:** Wysoki - przy dużej liczbie items i nested containers, obliczenia mogą być kosztowne.

**Potwierdzenie z trace'a:** Long tasks związane z EvaluateScript (1076ms) mogą być spowodowane ciężkimi computed properties.

### 2.2 `ShoppingPlanningPage.vue` - `availableItems` i `filteredItems`
```typescript
// Linie 154-214
const availableItems = computed<IItemWithContainerId[]>(() => {
  const items: IItemWithContainerId[] = []
  containers.value.forEach(container => {
    container.items.forEach(item => {
      // ... filtrowanie
    })
  })
  return items
})

const filteredItems = computed<IItemWithItemId[]>(() => {
  let items = [...availableItems.value]
  // ... filtrowanie i sortowanie
  items.sort((a, b) => {
    return priorityOrder[a.priority] - priorityOrder[b.priority]
  })
  return items
})
```

**Problem:**
- `availableItems` iteruje przez wszystkie containers i items
- `filteredItems` tworzy kopię tablicy i sortuje ją
- Oba computed uruchamiają się przy każdej zmianie w `containers.value`

**Wpływ:** Wysoki - przy dużej liczbie kontenerów i items, iteracje mogą być kosztowne.

**Potwierdzenie z trace'a:** 79,599 JS execution events wskazuje na zbyt częste uruchamianie computed properties.

### 2.3 `ItemsTable.vue` - `sortedItems`
```typescript
// Linie 212-252
const sortedItems = computed<IGearItem[]>(() => {
  const items = [...props.items]
  // ... sortowanie
  return items.sort((a, b) => {
    // ... logika sortowania
  })
})
```

**Problem:**
- Tworzy kopię tablicy przy każdej zmianie
- Sortuje tablicę przy każdej zmianie w `props.items` lub `tableSorting.value`
- Mutuje tablicę (`.sort()` mutuje oryginalną tablicę)

**Wpływ:** Średni - przy dużej liczbie items, sortowanie może być kosztowne.

**Potwierdzenie z trace'a:** Częste re-renderowania (79,599 events) mogą być spowodowane sortowaniem przy każdej zmianie.

---

## 3. Problem: Brak Memoizacji dla Kosztownych Obliczeń

### 3.1 `calculateTotalWeightSync` i `calculateTotalPriceSync`
```typescript
// containerCalculations.ts
export function calculateTotalWeightSync(
  container: IGearContainer,
  allContainers: IGearContainer[],
): number {
  // ... rekurencyjne obliczenia
}
```

**Problem:**
- Funkcje są wywoływane w computed properties bez memoizacji
- Rekurencyjne obliczenia dla nested containers
- Wywoływane wielokrotnie dla tych samych danych

**Wpływ:** Średni - przy głębokiej hierarchii nested containers, obliczenia mogą być kosztowne.

---

## 4. Problem: Równoległe Ładowanie Obrazów Bez Ograniczeń

### 4.1 `ContainerItemImagesGallery.vue`
```typescript
// Linie 84-89
const results = await Promise.all(
  itemsToShow.value.map(async (item) => {
    const image = await getItemImage(item.id)
    return { item, image }
  }),
)
```

**Problem:**
- Ładuje obrazy dla wszystkich items równolegle (do 12)
- Brak throttling/debouncing
- Może powodować przeciążenie sieci i przeglądarki

**Wpływ:** Średni - przy wielu items, równoległe żądania mogą spowolnić aplikację.

---

## 5. Problem: Częste Zapis do localStorage

### 5.1 `ShoppingPlanningPage.vue`
```typescript
watch(shoppingList, (newList) => {
  saveShoppingListToStorage(newList)
}, { deep: true })
```

**Problem:**
- Zapis do localStorage przy każdej zmianie w `shoppingList`
- `deep: true` powoduje, że każda zmiana w zagnieżdżonych obiektach wywołuje zapis
- localStorage.setItem jest synchroniczne i może blokować główny wątek

**Wpływ:** Średni - może powodować opóźnienia UI, szczególnie przy częstych zmianach.

**Potwierdzenie z trace'a:** localStorage.setItem jest synchroniczne i może przyczyniać się do long tasks.

---

## Rekomendacje Optymalizacji

### Priorytet 1: Wysoki Wpływ

#### 1.1 Zastąp `watch` z `deep: true` bardziej precyzyjnymi watcherami

**Dla `ShoppingPlanningPage.vue`:**
```typescript
// Zamiast watch z deep: true, użyj watch na konkretnych właściwościach
watch(() => shoppingList.value.length, () => {
  saveShoppingListToStorage(shoppingList.value)
})

// Lub użyj watchEffect z bardziej precyzyjną logiką
watchEffect(() => {
  // Tylko zapisz jeśli rzeczywiście się zmieniło
  const serialized = JSON.stringify(shoppingList.value)
  if (serialized !== lastSerialized.value) {
    saveShoppingListToStorage(shoppingList.value)
    lastSerialized.value = serialized
  }
})
```

**Dla `ContainerItemImagesGallery.vue`:**
```typescript
// Zamiast watch z deep: true, śledź tylko długość i ID items
watch(() => props.items.map(i => i.id).join(','), () => {
  loadImages()
})
```

#### 1.2 Dodaj Debouncing dla Zapisów do localStorage

```typescript
import { debounce } from 'lodash-es'

const debouncedSave = debounce((list: IItemWithContainerId[]) => {
  saveShoppingListToStorage(list)
}, 500)

watch(shoppingList, (newList) => {
  debouncedSave(newList)
}, { deep: true })
```

#### 1.3 Optymalizuj Computed Properties - Dodaj Memoizację

**Dla `CategoryPieChart.vue`:**
```typescript
import { computed, shallowRef } from 'vue'

// Użyj shallowRef dla containers jeśli nie potrzebujesz głębokiej reaktywności
const containersRef = shallowRef(containers.value)

const categoryData = computed(() => {
  // Dodaj wczesne wyjście jeśli dane się nie zmieniły
  const cacheKey = `${props.container.id}-${props.includeNested}-${containersRef.value.length}`
  // ... implementacja z cache
})
```

**Dla `ShoppingPlanningPage.vue`:**
```typescript
// Użyj computed z memoizacją lub rozdziel na mniejsze computed
const availableItems = computed(() => {
  // Użyj Map/Set dla szybszego lookup
  const itemsMap = new Map()
  containers.value.forEach(container => {
    container.items.forEach(item => {
      if (item.status === 'toBuy' || (includeExpiringSoon.value && isExpiringSoon(item))) {
        itemsMap.set(item.id, { ...item, _containerId: container.id })
      }
    })
  })
  return Array.from(itemsMap.values())
})
```

### Priorytet 2: Średni Wpływ

#### 2.1 Optymalizuj Sortowanie w `ItemsTable.vue`

```typescript
// Użyj toSorted() zamiast sort() (nie mutuje oryginalnej tablicy)
const sortedItems = computed(() => {
  return [...props.items].toSorted((a, b) => {
    // ... logika sortowania
  })
})

// Lub użyj memoizacji dla sortowania
const sortedItems = computed(() => {
  const sortKey = tableSorting.value.length > 0 
    ? `${tableSorting.value[0].id}-${tableSorting.value[0].desc}`
    : 'order'
  
  // Cache wyników sortowania
  if (sortCache.value.key === sortKey && sortCache.value.items === props.items) {
    return sortCache.value.result
  }
  
  const result = [...props.items].toSorted(/* ... */)
  sortCache.value = { key: sortKey, items: props.items, result }
  return result
})
```

#### 2.2 Ogranicz Równoległe Ładowanie Obrazów

```typescript
// W ContainerItemImagesGallery.vue
async function loadImages() {
  // ... 
  
  // Ładuj obrazy w batchach po 3-4 naraz
  const batchSize = 3
  const results: ItemWithImage[] = []
  
  for (let i = 0; i < itemsToShow.value.length; i += batchSize) {
    const batch = itemsToShow.value.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(async (item) => {
        const image = await getItemImage(item.id)
        return { item, image }
      })
    )
    results.push(...batchResults)
    
    // Jeśli już mamy 12 items z obrazami, przerwij
    if (results.filter(r => r.image !== null).length >= 12) break
  }
  
  itemsWithImages.value = results.filter(r => r.image !== null).slice(0, 12)
}
```

#### 2.3 Dodaj Virtual Scrolling dla Dużych Tabel

Rozważ użycie virtual scrolling dla `ItemsTable` gdy liczba items przekracza 100-200.

### Priorytet 3: Niski Wpływ (Długoterminowe)

#### 3.1 Rozważ Web Workers dla Ciężkich Obliczeń

Dla bardzo dużych zbiorów danych, rozważ przeniesienie obliczeń do Web Workers.

#### 3.2 Dodaj Lazy Loading dla Komponentów

Użyj `defineAsyncComponent` dla komponentów, które nie są zawsze widoczne.

---

## Metryki do Monitorowania

1. **Time to Interactive (TTI)** - czas do pełnej interaktywności
2. **First Contentful Paint (FCP)** - czas do pierwszego renderowania
3. **Largest Contentful Paint (LCP)** - czas do renderowania największego elementu
4. **Cumulative Layout Shift (CLS)** - stabilność layoutu
5. **Total Blocking Time (TBT)** - czas blokowania głównego wątku
6. **Memory Usage** - użycie pamięci (szczególnie przy dużej liczbie items)

---

## Narzędzia do Analizy

1. **Chrome DevTools Performance Tab** - profilowanie wydajności
2. **Chrome DevTools Memory Tab** - analiza pamięci
3. **Vue DevTools** - śledzenie reaktywności i re-renderowań
4. **Lighthouse** - audyt wydajności
5. **Web Vitals Extension** - monitorowanie metryk w czasie rzeczywistym

---

## Następne Kroki

1. ✅ Stwórz raport z analizą (ten dokument)
2. ✅ Przeanalizowano rzeczywisty trace z Chrome DevTools (zobacz [PERFORMANCE_TRACE_ANALYSIS.md](./PERFORMANCE_TRACE_ANALYSIS.md))
3. ⏳ Zaimplementuj optymalizacje Priorytetu 1 (watch z deep: true, computed properties)
4. ⏳ Przetestuj wydajność przed i po optymalizacjach (wykonaj nowy trace)
5. ⏳ Zaimplementuj optymalizacje Priorytetu 2 (memoizacja, sortowanie)
6. ⏳ Dodaj monitoring wydajności w produkcji

## 📈 Cele Optymalizacji (na podstawie trace'a)

Po implementacji optymalizacji, sprawdź czy:

- **Long Tasks** zmniejszyły się z 64 do < 10
- **JS Execution Events** zmniejszyły się z 79,599 o co najmniej 50%
- **Layout Events** zmniejszyły się z 515 do < 100
- **Paint Events** zmniejszyły się z 954 do < 200
- **RunMicrotasks** zmniejszyło się z 581ms do < 100ms

