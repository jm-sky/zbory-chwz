# Analiza Trace'a Wydajności - Chrome DevTools

**Data:** 2025-12-02  
**Czas trwania trace'a:** 8.14 sekundy  
**Plik:** `docs/tmp/Trace-20251202T131105.json`

## 📊 Podsumowanie

### Główne Problemy

1. **⚠️ 64 Long Tasks (>50ms)** - **KRYTYCZNE**
   - Najdłuższy task: **1076.99ms** (ponad 1 sekunda!)
   - Łączny czas w long tasks: **17,438ms** (ponad 17 sekund podczas 8-sekundowego trace'a!)
   - To oznacza, że główny wątek był blokowany przez większość czasu

2. **⚠️ 79,599 JavaScript Execution Events** - **WYSOKIE**
   - Średni czas: 0.42ms
   - Maksymalny czas: 1076.99ms
   - Łączny czas JS: 33,039ms

3. **⚠️ 515 Layout Events** - **ŚREDNIE**
   - Łączny czas: 65.93ms
   - Głównie: UpdateLayoutTree (52.16ms), Layout (7.39ms)

4. **⚠️ 954 Paint Events** - **ŚREDNIE**
   - Łączny czas: 19.96ms
   - Głównie: Paint (11.13ms), PrePaint (8.78ms)

## 🔍 Szczegółowa Analiza Long Tasks

### Top 10 Najdłuższych Tasks:

1. **RunTask: 1076.99ms** - Prawdopodobnie inicjalizacja lub ciężkie obliczenia
2. **EvaluateScript: 1076.88ms** - Wykonywanie dużego skryptu JavaScript
3. **V8.StackGuard: 1071.86ms** - V8 engine overhead
4. **V8.HandleInterrupts: 1071.85ms** - V8 engine overhead
5. **V8.InvokeApiInterruptCallbacks: 1071.84ms** - V8 engine overhead
6. **CpuProfiler::StartProfiling: 1071.06ms** - Profiling overhead (można wyłączyć)
7. **RunTask: 634.49ms** - Kolejny długi task
8. **RunMicrotasks: 581.45ms** - Wykonywanie microtasks (Promise callbacks, etc.)
9. **BackgroundProcessor::RunScriptStreamingTask: 316.30ms** - Parsowanie JavaScript
10. **v8.parseOnBackground: 316.29ms** - Parsowanie JavaScript

### Analiza:

- **Pierwsze 6 tasks** (około 6.5 sekundy) wydają się być związane z **inicjalizacją/profilingiem**
- **RunMicrotasks: 581ms** - może oznaczać zbyt wiele Promise callbacks lub watchers Vue
- **Parsowanie JavaScript** - wiele plików jest parsowanych w tle

## 💡 Rekomendacje

### Priorytet 1: KRYTYCZNE - Long Tasks

#### 1.1 Zoptymalizuj Ciężkie Computed Properties

**Problem:** Computed properties wykonują się zbyt często lub są zbyt ciężkie.

**Rozwiązanie:**
- Dodaj memoizację dla ciężkich obliczeń
- Użyj `shallowRef` zamiast `ref` dla dużych obiektów
- Rozdziel ciężkie computed na mniejsze, bardziej specyficzne

**Lokalizacje do sprawdzenia:**
- `CategoryPieChart.vue` - `categoryData` computed
- `ShoppingPlanningPage.vue` - `availableItems`, `filteredItems`
- `ItemsTable.vue` - `sortedItems`

#### 1.2 Zoptymalizuj Watch z `deep: true`

**Problem:** Watch z `deep: true` uruchamia się przy każdej zmianie w zagnieżdżonych obiektach.

**Rozwiązanie:**
```typescript
// Zamiast:
watch(shoppingList, (newList) => {
  saveShoppingListToStorage(newList)
}, { deep: true })

// Użyj:
watch(() => shoppingList.value.length, () => {
  saveShoppingListToStorage(shoppingList.value)
})

// Lub debouncing:
import { debounce } from 'lodash-es'
const debouncedSave = debounce((list) => {
  saveShoppingListToStorage(list)
}, 500)

watch(shoppingList, debouncedSave, { deep: true })
```

**Lokalizacje:**
- `ShoppingPlanningPage.vue` - watch na `containers`, `shoppingList`, `deletedItems`
- `ContainerItemImagesGallery.vue` - watch na `props.items`
- `ItemsTable.vue` - watch na `columnVisibility`, `tableSorting`

#### 1.3 Ogranicz RunMicrotasks (581ms)

**Problem:** Zbyt wiele microtasks (Promise callbacks, watchers Vue).

**Rozwiązanie:**
- Sprawdź czy watchers Vue nie uruchamiają się zbyt często
- Użyj `nextTick` tylko gdy konieczne
- Rozważ batchowanie aktualizacji

### Priorytet 2: WYSOKIE - JavaScript Execution Events

#### 2.1 Zmniejsz Liczbę Re-renderowań

**Problem:** 79,599 JS execution events oznacza bardzo częste re-renderowanie.

**Rozwiązanie:**
- Użyj `v-once` dla statycznych elementów
- Użyj `v-memo` dla list z dużą liczbą elementów
- Sprawdź czy komponenty nie renderują się niepotrzebnie

**Przykład:**
```vue
<!-- Dla statycznych list -->
<div v-for="item in items" :key="item.id" v-memo="[item.id, item.name]">
  {{ item.name }}
</div>
```

#### 2.2 Optymalizuj Sortowanie i Filtrowanie

**Problem:** `sortedItems` w `ItemsTable.vue` sortuje przy każdej zmianie.

**Rozwiązanie:**
```typescript
// Dodaj cache dla sortowania
const sortCache = ref<{ key: string, result: IGearItem[] } | null>(null)

const sortedItems = computed(() => {
  const sortKey = tableSorting.value.length > 0 
    ? `${tableSorting.value[0].id}-${tableSorting.value[0].desc}`
    : 'order'
  
  // Użyj cache jeśli dane się nie zmieniły
  if (sortCache.value?.key === sortKey && 
      sortCache.value.items === props.items) {
    return sortCache.value.result
  }
  
  const result = [...props.items].toSorted(/* ... */)
  sortCache.value = { key: sortKey, items: props.items, result }
  return result
})
```

### Priorytet 3: ŚREDNIE - Layout i Paint Events

#### 3.1 Zmniejsz Forced Reflows

**Problem:** 515 layout events może oznaczać forced reflows.

**Rozwiązanie:**
- Unikaj odczytywania `offsetHeight`, `scrollTop` itp. podczas pisania
- Użyj `requestAnimationFrame` dla animacji
- Grupuj zmiany DOM

#### 3.2 Optymalizuj Paint Events

**Problem:** 954 paint events może oznaczać niepotrzebne repainty.

**Rozwiązanie:**
- Użyj CSS `transform` zamiast zmiany `top/left`
- Użyj `will-change` dla elementów, które będą animowane
- Unikaj zmiany właściwości, które triggerują paint (background-color, border, etc.)

## 📈 Metryki do Monitorowania

Po implementacji optymalizacji, sprawdź czy:

1. **Long Tasks** zmniejszyły się do < 10
2. **JS Execution Events** zmniejszyły się o co najmniej 50%
3. **Layout Events** zmniejszyły się do < 100
4. **Paint Events** zmniejszyły się do < 200

## 🎯 Plan Działania

1. ✅ **Zidentyfikowano problemy** (ten dokument)
2. ⏳ **Zoptymalizuj watch z `deep: true`** (Priorytet 1.2)
3. ⏳ **Zoptymalizuj computed properties** (Priorytet 1.1)
4. ⏳ **Dodaj memoizację dla sortowania** (Priorytet 2.2)
5. ⏳ **Zmniejsz re-renderowania** (Priorytet 2.1)
6. ⏳ **Przetestuj ponownie** - wykonaj nowy trace i porównaj wyniki

## 📊 Dodatkowe Metryki z Trace'a

### Event Categories Breakdown (Top 10):

1. **disabled-by-default-devtools.timeline**: 59,154 (41.78%)
   - Głównie DevTools overhead - może być ignorowane w produkcji

2. **devtools.timeline,disabled-by-default-v8.gc**: 22,017 (15.55%)
   - Garbage Collection events - normalne, ale warto monitorować

3. **cppgc**: 8,617 (6.09%)
   - C++ Garbage Collection

4. **devtools.timeline**: 8,103 (5.72%)
   - DevTools timeline events

5. **blink.user_timing**: 7,779 (5.49%)
   - User timing marks - performance marks z aplikacji

6. **loading**: 6,592 (4.66%)
   - Network loading events

7. **disabled-by-default-v8.inspector**: 5,921 (4.18%)
   - V8 inspector events

8. **v8**: 5,090 (3.59%)
   - V8 engine events

9. **cc,benchmark,disabled-by-default-devtools.timeline.frame**: 4,370 (3.09%)
   - Compositor events

10. **v8.execute**: 3,887 (2.75%)
    - V8 execution events

### Network Events:

- **Total events**: 8,281
- Większość to prawdopodobnie Vite HMR (Hot Module Replacement) w trybie dev
- W produkcji liczba powinna być znacznie niższa

### Memory Events:

- **Total events**: 23,246
- Głównie V8 Garbage Collection events:
  - `V8.GC_TIME_TO_SAFEPOINT`
  - `V8.GC_MC_COMPLETE_SWEEPING`
  - `V8.GC_MC_SWEEP`
- Wysoka liczba GC events może wskazywać na:
  - Zbyt częste tworzenie/tracone obiektów
  - Możliwe memory leaks
  - Warto monitorować użycie pamięci w Vue DevTools

### Vue/React Analysis:

- **Found**: 3 potential Vue/React events (bardzo mało)
- Wszystkie związane z PrerenderHostRegistry (Chrome feature, nie Vue)
- Trace nie zawiera bezpośrednich Vue events - może być potrzebne włączenie Vue DevTools podczas trace'a

## 📝 Notatki

- Trace zawiera **141,597 eventów** w ciągu 8.14 sekundy
- Większość czasu (17+ sekund w long tasks podczas 8-sekundowego trace'a) jest spędzana na blokowaniu głównego wątku
- Profiling overhead (`CpuProfiler::StartProfiling: 1071ms`) może być wyłączony w produkcji
- Wiele eventów związanych z V8 engine może być normalne, ale warto sprawdzić czy nie ma memory leaks
- **23,246 Memory Events** - wysoka liczba GC events może wskazywać na problemy z zarządzaniem pamięcią
- **8,281 Network Events** - większość to prawdopodobnie Vite HMR w trybie dev
- **59,154 DevTools timeline events** - większość to overhead DevTools, nie aplikacji

