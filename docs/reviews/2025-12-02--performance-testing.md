# Instrukcja Testowania Wydajności w Chrome DevTools

## Krok 1: Otwórz Chrome DevTools

1. Otwórz aplikację w Chrome: `http://localhost:5177`
2. Naciśnij `F12` lub `Ctrl+Shift+I` (Linux/Windows) / `Cmd+Option+I` (Mac)
3. Przejdź do zakładki **Performance** (lub **Performance Monitor**)

## Krok 2: Nagraj Profil Wydajności

1. Kliknij przycisk **Record** (🔴) w DevTools Performance tab
2. Wykonaj typowe akcje:
   - Przejdź do strony z kontenerami (`/gear`)
   - Otwórz szczegóły kontenera (kliknij na kontener)
   - Jeśli jest tabela z items:
     - Wpisz coś w wyszukiwarkę
     - Zmień sortowanie (kliknij nagłówek kolumny)
     - Przełącz tryb edycji (jeśli dostępny)
     - Edytuj kilka items
   - Przejdź do strony Shopping Planning (`/gear/shopping`)
   - Przejdź do strony All Items (`/gear/items`)
3. Zatrzymaj nagrywanie (kliknij przycisk Stop)

## Krok 3: Przeanalizuj Wyniki

### Co szukać:

1. **Long Tasks** (żółte bloki >50ms)
   - Oznaczają blokowanie głównego wątku
   - Powinny być jak najkrótsze

2. **FPS (Frames Per Second)**
   - Powinno być stabilne 60 FPS
   - Spadki poniżej 30 FPS oznaczają problemy

3. **Memory Usage**
   - Sprawdź czy pamięć rośnie (memory leak)
   - Kliknij przycisk "Collect garbage" (🗑️) przed i po akcjach

4. **JavaScript Execution Time**
   - Sprawdź ile czasu zajmuje wykonanie JavaScript
   - Szukaj funkcji, które zajmują dużo czasu

5. **Layout Shifts (CLS)**
   - Sprawdź czy są nieoczekiwane przesunięcia layoutu

## Krok 4: Użyj Performance Monitor

1. Otwórz zakładkę **Performance Monitor** (w DevTools)
2. Włącz monitoring:
   - CPU usage
   - JS heap size
   - DOM nodes
   - Event listeners
3. Wykonaj akcje i obserwuj metryki w czasie rzeczywistym

## Krok 5: Użyj Memory Profiler

1. Przejdź do zakładki **Memory**
2. Zrób snapshot przed akcjami
3. Wykonaj akcje
4. Zrób snapshot po akcjach
5. Porównaj snapshots - szukaj:
   - Wzrostu liczby obiektów Vue
   - Wzrostu liczby watchers
   - Memory leaks (obiekty, które nie powinny istnieć)

## Krok 6: Użyj Performance API w Konsoli

1. Otwórz zakładkę **Console** w DevTools
2. Użyj Performance API do pomiaru wydajności:

```javascript
// Sprawdź metryki ładowania
const navigationTiming = performance.getEntriesByType('navigation')[0]
const paintTiming = performance.getEntriesByType('paint')
console.log('DOM Content Loaded:', navigationTiming.domContentLoadedEventEnd - navigationTiming.domContentLoadedEventStart, 'ms')
console.log('First Paint:', paintTiming.find(p => p.name === 'first-paint')?.startTime || 'N/A', 'ms')

// Sprawdź pamięć (jeśli dostępne)
if (performance.memory) {
  console.log('Used:', (performance.memory.usedJSHeapSize / 1048576).toFixed(2), 'MB')
}

// Sprawdź long tasks
const longTasks = performance.getEntriesByType('longtask')
console.log('Long tasks:', longTasks.length)
```

Alternatywnie, użyj skryptu `scripts/analyze-trace.js` do analizy zapisanego trace'a.

## Krok 7: Sprawdź Network Tab

1. Przejdź do zakładki **Network**
2. Odśwież stronę (F5)
3. Sprawdź:
   - Czas ładowania każdego requestu
   - Rozmiar plików
   - Czy są duplikaty requestów
   - Czy są niepotrzebne requesty

## Typowe Problemy do Sprawdzenia:

### 1. Watch z deep: true
- Otwórz Vue DevTools (jeśli zainstalowane)
- Sprawdź liczbę watchers
- Wykonaj akcję i sprawdź ile watchers się uruchomiło

### 2. Computed Properties
- W Vue DevTools sprawdź computed properties
- Sprawdź czy są wywoływane zbyt często
- Sprawdź czy wykonują ciężkie obliczenia

### 3. Re-renderowanie
- W React DevTools (lub Vue DevTools) włącz "Highlight updates"
- Sprawdź które komponenty renderują się zbyt często

### 4. Memory Leaks
- Wykonaj akcje wielokrotnie
- Sprawdź czy pamięć rośnie
- Sprawdź czy są event listeners, które nie są czyszczone

## Metryki do Zapisania:

Po wykonaniu testów, zapisz następujące metryki:

- **Time to Interactive (TTI)**: _____ ms
- **First Contentful Paint (FCP)**: _____ ms
- **Largest Contentful Paint (LCP)**: _____ ms
- **Total Blocking Time (TBT)**: _____ ms
- **Cumulative Layout Shift (CLS)**: _____
- **Memory Usage**: _____ MB
- **Long Tasks Count**: _____
- **Average Long Task Duration**: _____ ms
- **FPS (average)**: _____
- **FPS (min)**: _____

## Raportowanie Problemów:

Gdy znajdziesz problemy, zapisz:
1. Co robiłeś (kroki reprodukcji)
2. Co się stało (symptomy)
3. Screenshot z Performance tab
4. Screenshot z Memory profiler (jeśli dotyczy)
5. Console errors/warnings (jeśli są)

