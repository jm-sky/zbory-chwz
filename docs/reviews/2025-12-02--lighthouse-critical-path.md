# Analiza Critical Path - Lighthouse Report

**Data:** 2025-12-02  
**Maximum Critical Path Latency:** 2,582 ms

## 📊 Analiza Critical Path

### Najdłuższe Operacje:

1. **`/auth/me` (API call)** - **2,582 ms** ⚠️ **KRYTYCZNE**
   - To jest największy bottleneck!
   - API call blokuje cały critical path
   - 0.43 KiB - mały rozmiar, ale bardzo długi czas odpowiedzi

2. **`ContainerDetailPage.vue`** - **1,047 ms**
   - Duży komponent (49.47 KiB)
   - Ładowany synchronicznie w critical path

3. **`AiChatMessage.vue` (CSS)** - **1,481 ms**
   - Style komponentu (2.67 KiB)
   - Ładowany synchronicznie

4. **`AiChatWindow.vue`** - **1,193 ms**
   - Komponent (20.34 KiB)
   - Ładowany synchronicznie

5. **`vue-sonner.js`** - **657 ms**
   - Biblioteka (46.96 KiB)
   - Ładowana synchronicznie

### Critical Path Timeline:

```
0ms     → /gear/fcd6542e-4203-4b36-9ebf-6c503d14fb7f (384ms)
384ms   → /src/main.ts (387ms)
387ms   → /src/App.vue (466ms)
466ms   → sonner/index.ts (559ms)
559ms   → sonner/Sonner.vue (612ms)
612ms   → vue-sonner.js (657ms)
657ms   → ContainerDetailPage.vue (1,047ms)
1,047ms → AiChatDialog.vue (1,080ms)
1,080ms → AiChatWindow.vue (1,193ms)
1,193ms → AiChatMessage.vue (1,317ms)
1,317ms → AiChatMessage.vue CSS (1,481ms)
1,481ms → /auth/me API (2,582ms) ⚠️ BOTTLENECK
```

## 🔴 Główne Problemy

### 1. API Call `/auth/me` Blokuje Critical Path (2,582ms)

**Problem:**
- API call do `/auth/me` jest wykonywany synchronicznie w critical path
- Blokuje renderowanie strony przez 2.5 sekundy
- Mały rozmiar (0.43 KiB) ale bardzo długi czas odpowiedzi

**Możliwe przyczyny:**
- Backend jest wolny
- Sieć jest wolna
- Request jest wykonywany przed innymi operacjami
- Brak cache dla danych użytkownika

### 2. Sekwencyjne Ładowanie Komponentów

**Problem:**
- Komponenty są ładowane sekwencyjnie zamiast równolegle
- `ContainerDetailPage.vue` (1,047ms) blokuje dalsze ładowanie
- Komponenty AI (`AiChatDialog`, `AiChatWindow`, `AiChatMessage`) są ładowane synchronicznie

**Rozwiązanie:**
- Lazy loading dla komponentów niekrytycznych
- Code splitting dla AI components
- Preload dla krytycznych komponentów

### 3. Duże Bundle Sizes

**Problem:**
- `vue-sonner.js`: 46.96 KiB
- `ContainerDetailPage.vue`: 49.47 KiB
- `AiChatWindow.vue`: 20.34 KiB

**Rozwiązanie:**
- Tree shaking
- Lazy loading
- Code splitting

## 💡 Rekomendacje Optymalizacji

### Priorytet 1: KRYTYCZNE - API Call `/auth/me`

#### 1.1 Sprawdź Backend Performance

```bash
# Sprawdź czas odpowiedzi backendu
curl -w "@curl-format.txt" http://localhost:8000/api/auth/me
```

**Możliwe rozwiązania:**
- Optymalizacja query w backendzie
- Dodanie cache dla danych użytkownika
- Sprawdzenie czy nie ma N+1 queries

#### 1.2 Przenieś `/auth/me` poza Critical Path

**Obecnie:** API call jest prawdopodobnie wykonywany w `onMounted` lub `setup` komponentu

**Rozwiązanie:**
```typescript
// Zamiast:
onMounted(async () => {
  const user = await apiClient.get('/auth/me') // Blokuje renderowanie
})

// Użyj:
// 1. Załaduj dane użytkownika asynchronicznie po pierwszym renderze
onMounted(() => {
  nextTick(() => {
    loadUserData() // Nie blokuje initial render
  })
})

// 2. Lub użyj Suspense dla async components
```

#### 1.3 Dodaj Cache dla Danych Użytkownika

```typescript
// Cache w localStorage lub memory cache
const cachedUser = localStorage.getItem('user')
if (cachedUser) {
  // Użyj cached data, załaduj fresh data w tle
  useUserStore().setUser(JSON.parse(cachedUser))
  // Load fresh data async
  loadFreshUserData()
}
```

### Priorytet 2: WYSOKIE - Lazy Loading Komponentów

#### 2.1 Lazy Load AI Components

**Problem:** Komponenty AI są ładowane synchronicznie, ale nie są potrzebne od razu

**Rozwiązanie:**
```typescript
// W routerze lub komponencie
const AiChatDialog = defineAsyncComponent(() => 
  import('@/modules/ai/components/AiChatDialog.vue')
)

const AiChatWindow = defineAsyncComponent(() => 
  import('@/modules/ai/components/AiChatWindow.vue')
)
```

#### 2.2 Lazy Load ContainerDetailPage

**Problem:** `ContainerDetailPage.vue` jest duży (49.47 KiB) i ładowany synchronicznie

**Rozwiązanie:**
```typescript
// W routerze
{
  path: GearRoutePath.ContainerDetail,
  name: GearRouteName.ContainerDetail,
  component: () => import('@/modules/gear/pages/ContainerDetailPage.vue'),
  // ...
}
```

**Uwaga:** Sprawdź czy już jest lazy loaded w routerze!

#### 2.3 Lazy Load Sonner (Toast Notifications)

**Problem:** `vue-sonner.js` (46.96 KiB) jest ładowany synchronicznie

**Rozwiązanie:**
```typescript
// Lazy load tylko gdy potrzebne
const Sonner = defineAsyncComponent(() => 
  import('vue-sonner').then(m => m.Sonner)
)
```

### Priorytet 3: ŚREDNIE - Code Splitting i Preloading

#### 3.1 Preload Krytycznych Komponentów

```typescript
// W main.ts lub App.vue
const link = document.createElement('link')
link.rel = 'preload'
link.href = '/src/modules/gear/pages/ContainerDetailPage.vue'
link.as = 'script'
document.head.appendChild(link)
```

#### 3.2 Code Splitting dla AI Module

```typescript
// Utwórz osobny chunk dla AI
const aiRoutes = {
  path: '/ai',
  component: () => import(/* webpackChunkName: "ai" */ '@/modules/ai/pages/AiPage.vue')
}
```

## 📈 Oczekiwane Ulepszenia

Po implementacji optymalizacji:

1. **Critical Path Latency** powinien zmniejszyć się z **2,582ms** do **< 1,000ms**
   - Głównie przez przeniesienie `/auth/me` poza critical path
   - Lazy loading komponentów AI

2. **Time to Interactive (TTI)** powinien się poprawić
   - Mniej blokowania przez synchroniczne operacje

3. **First Contentful Paint (FCP)** powinien się poprawić
   - Mniejsze bundle sizes przez code splitting

## 🎯 Plan Działania

1. ✅ **Zoptymalizowano `/auth/me` query** - użyto `placeholderData` z authStore
2. ✅ **Lazy load AI components** - `AiChatDialog` w ContainerDetailPage
3. ✅ **ContainerDetailPage jest już lazy loaded** - w routerze
4. ⏳ **Sprawdź backend performance** - `/auth/me` endpoint (2.5 sekundy to bardzo długo!)
5. ⏳ **Dodaj cache dla danych użytkownika w localStorage** - background refresh
6. ⏳ **Przetestuj ponownie** - wykonaj nowy Lighthouse audit

## ✅ Zaimplementowane Optymalizacje

### 1. useCurrentUser - placeholderData
**Zmiana:** Dodano `placeholderData: authStore.user ?? undefined` i `refetchOnMount: !authStore.user`
**Efekt:** Query nie blokuje critical path - używa danych z store, wykonuje się w tle

### 2. Lazy Load Komponentów Dialogowych i Niekrytycznych

#### ContainerDetailPage:
- `AiChatDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `AddNestedContainerDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `ExportToPromptDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `ExportToCSVDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `CategoryPieChart` - lazy loaded (nie krytyczny dla initial render)

#### ShoppingPlanningPage:
- `AddItemToShoppingDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `ShoppingExportDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)

#### ContainersListPage:
- `ExportToCSVDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `ExportToPromptDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)
- `ImportMarkdownDialog` - lazy loaded (tylko gdy użytkownik otworzy dialog)

#### ItemDetailPage:
- `ItemImageGallery` - lazy loaded (nie krytyczny dla initial render)

**Efekt:** Znacznie mniejszy initial bundle size, szybszy Time to Interactive (TTI)

## 📝 Notatki

- **Maximum Critical Path Latency: 2,582ms** - głównie przez `/auth/me` API call
- Większość czasu (1.5 sekundy) jest spędzana na ładowaniu komponentów Vue
- API call `/auth/me` jest największym bottleneck (2.5 sekundy)
- Komponenty AI są ładowane synchronicznie, ale nie są potrzebne od razu

