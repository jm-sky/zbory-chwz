# FEATURE-028: Nawigacja przycisku "Wróć"

**Status:** ✅ Completed  
**Priority:** High  
**Complexity:** Small  
**Related:** [2026-03-01--feature-026-query-params-refactoring.md](./2026-03-01--feature-026-query-params-refactoring.md), [2026-07-09--query-params-analysis.md](../reviews/2026-07-09--query-params-analysis.md)

## 📋 Opis

Dokumentacja zachowania przycisku "Wróć" w różnych komponentach aplikacji, wyjaśniająca jak działa nawigacja w różnych scenariuszach i dlaczego używa parametru `from` zamiast `router.back()`.

## 🎯 Problem

Po commit d7ce6d2f5d142f318050496b470771a20082413a zmieniono przyciski "Wróć" na użycie `router.back()`, co powodowało nieprawidłowe zachowanie:

1. Użytkownik: ContainersList → ContainerDetails → ItemDetails
2. Użytkownik klika "Edytuj" → ItemEdit
3. Po zapisie `navigateBackAndClean()` nawiguje do ItemDetails (dodaje wpis do historii)
4. Historia przeglądarki: ItemDetails → ItemEdit → ItemDetails (po zapisie)
5. Kliknięcie "Wróć" w ItemDetails używa `router.back()` → wraca do ItemEdit zamiast ContainerDetails ❌

## ✅ Rozwiązanie

Przywrócenie logiki nawigacji opartej na parametrze `from` z query string zamiast polegania na historii przeglądarki. Parametr `from` jest zachowywany podczas nawigacji, co zapewnia poprawną nawigację wstecz niezależnie od historii przeglądarki.

## 📋 Lista wszystkich komponentów z przyciskiem "Wróć"

Poniżej znajduje się pełna lista wszystkich komponentów i stron w aplikacji, które zawierają przycisk "Wróć":

| # | Komponent/Strona | Lokalizacja | Metoda nawigacji | Użycie |
|---|------------------|-------------|------------------|--------|
| 1 | **ItemHeader.vue** | `src/modules/gear/components/ItemHeader.vue` | Parametr `from` z query string | `ItemDetailPage` |
| 2 | **ContainerHeader.vue** | `src/modules/gear/components/ContainerHeader.vue` | `router.back()` | `ContainerDetailPage` |
| 3 | **PublicContainerHeader.vue** | `src/modules/gear/components/PublicContainerHeader.vue` | Prop `backPath` lub emit `back` | `PublicContainerDetailPage`, `SharedContainerDetailPage` |
| 4 | **PublicItemDetailPage.vue** | `src/modules/gear/pages/PublicItemDetailPage.vue` | Explicit navigation | Strona szczegółów publicznego przedmiotu |
| 5 | **ContainerShareTokensPage.vue** | `src/modules/gear/pages/ContainerShareTokensPage.vue` | Explicit navigation | Strona zarządzania tokenami udostępniania |
| 6 | **ProfileEditPage.vue** | `src/modules/user/pages/ProfileEditPage.vue` | Explicit navigation | Strona edycji profilu użytkownika |
| 7 | **TwoFactorSetupPage.vue** | `src/modules/auth/pages/TwoFactorSetupPage.vue` | `ButtonLink` | Strona konfiguracji 2FA |
| 8 | **CatalogueItemDetailPage.vue** | `src/modules/gear/pages/catalogue/CatalogueItemDetailPage.vue` | Explicit navigation | Strona szczegółów przedmiotu z katalogu |

## 🔍 Jak działa nawigacja "Wróć"

### Parametr `from`

Parametr `from` określa źródło nawigacji do strony i jest używany przez przycisk "Wróć" do określenia, dokąd powinien nawigować.

**Możliwe wartości:**
- `'all-items'` - nawigacja z `AllItemsPage`
- `'container'` - nawigacja z `ContainerDetailPage` (przez `ItemsTable` lub `ContainerItemImageCard`)
- `undefined` - domyślnie nawigacja do kontenera

### Komponenty z przyciskiem "Wróć"

Poniżej znajduje się pełna lista wszystkich komponentów w aplikacji, które zawierają przycisk "Wróć":

#### 1. ItemHeader.vue

**Lokalizacja:** `src/modules/gear/components/ItemHeader.vue`  
**Użycie:** Wyświetlany na stronie `ItemDetailPage`  
**Metoda nawigacji:** Parametr `from` z query string

**Logika nawigacji:**
```typescript
const backTo = computed<string>(() => {
  const from = getFrom(route)
  if (from === 'all-items') {
    return GearRoutePath.AllItems
  }
  return GearRoutePath.ContainerDetailById(containerId)
})

const handleBack = () => {
  router.push(backTo.value)
}
```

**Scenariusze:**

1. **ContainersList → ContainerDetails → ItemDetails**
   - Parametr `from`: `'container'` (ustawiany przez `ItemsTable.navigateToItem()`)
   - Przycisk "Wróć" → `ContainerDetailById(containerId)` ✅

2. **AllItemsPage → ItemDetails**
   - Parametr `from`: `'all-items'` (ustawiany przez `AllItemsPage`)
   - Przycisk "Wróć" → `AllItemsPage` ✅

3. **ContainersList → ContainerDetails → ItemDetails → Edit → Save**
   - Parametr `from`: `'container'` (zachowywany przez `navigateBackAndClean()`)
   - Po zapisie: nawigacja do `ItemDetails` z `from=container`
   - Przycisk "Wróć" → `ContainerDetailById(containerId)` ✅

4. **AllItemsPage → ItemDetails → Edit → Save**
   - Parametr `from`: `'all-items'` (zachowywany przez `navigateBackAndClean()`)
   - Po zapisie: nawigacja do `ItemDetails` z `from=all-items`
   - Przycisk "Wróć" → `AllItemsPage` ✅

#### 2. ContainerHeader.vue

**Lokalizacja:** `src/modules/gear/components/ContainerHeader.vue`  
**Użycie:** Wyświetlany na stronie `ContainerDetailPage`  
**Metoda nawigacji:** Explicit navigation do `GearRoutePath.Containers` ⚠️ **Wymaga poprawki**

**Obecna logika nawigacji:**
```typescript
const handleBack = () => {
  router.push(GearRoutePath.Containers)
}
```

**Problemy z obecnym podejściem:**
- `ContainerDetailPage` może być otwarty z różnych miejsc:
  - `ContainersList` (główna lista) → oczekiwane: powrót do `ContainersList` ✅
  - `AllItemsPage` (kliknięcie w kontener) → oczekiwane: powrót do `AllItemsPage` ❌ (obecnie wraca do `ContainersList`)
  - `ContainerFormPage` (po zapisie edycji) → oczekiwane: powrót do poprzedniej strony ❌ (obecnie wraca do `ContainersList`)
  - `ContainerShareTokensPage` (po zarządzaniu tokenami) → oczekiwane: powrót do `ContainerDetailPage` ✅
  - Bezpośrednie linki (zakładki, emaile) → oczekiwane: powrót do `ContainersList` ✅
- Obecna implementacja zawsze nawiguje do `ContainersList`, co nie uwzględnia kontekstu nawigacji
- Użytkownik przychodzący z `AllItemsPage` oczekuje powrotu do `AllItemsPage`, a nie do `ContainersList`

**Przypadek użycia - problem:**
1. Użytkownik otwiera `/gear/items` (AllItemsPage)
2. Wybiera na liście kontener → otwiera się `/gear/01KBYM0E0D3STQ8Z279HMDQWKB` (ContainerDetailPage)
3. Klika "Edytuj" → otwiera się `/gear/01KBYM0E0D3STQ8Z279HMDQWKB/edit` (ContainerFormPage)
4. Klika "Zapisz" → otwiera się znowu `/gear/01KBYM0E0D3STQ8Z279HMDQWKB` (ContainerDetailPage)
5. Klika "Wstecz" → otwiera się `/gear` (ContainersList) ❌
   - **Oczekiwane:** `/gear/items` (AllItemsPage) ✅

**Proponowana poprawka - użycie parametru `from`:**

Podobnie jak w `ItemHeader.vue`, użyjemy parametru `from` z query string do określenia źródła nawigacji:

```typescript
import { useRoute } from 'vue-router'
import { getFrom } from '../utils/navigationParams'
import { GearRoutePath } from '../routes'

const route = useRoute()

const backTo = computed<string>(() => {
  const from = getFrom(route)
  if (from === 'all-items') {
    return GearRoutePath.AllItems
  }
  // Domyślnie wracamy do ContainersList
  return GearRoutePath.Containers
})

const handleBack = () => {
  router.push(backTo.value)
}
```

**Wymagane zmiany w innych miejscach:**

1. **AllItemsPage.vue** - dodać parametr `from='all-items'` przy nawigacji do `ContainerDetailPage`:
   ```typescript
   // Linia 355: gdy klikamy na kontener w kolumnie name
   :to="row.original.isContainer 
     ? { path: GearRoutePath.ContainerDetailById(row.original.id), query: createNavigationQuery(undefined, 'all-items') }
     : { path: GearRoutePath.ItemDetailById(row.original.containerId, row.original.id), query: createNavigationQuery(undefined, 'all-items') }"
   
   // Linia 369: gdy klikamy na kontener w kolumnie container
   :to="{ path: GearRoutePath.ContainerDetailById(row.original.containerId), query: createNavigationQuery(undefined, 'all-items') }"
   ```

2. **ContainerFormPage.vue** - zachować parametr `from` przy nawigacji po zapisie:
   ```typescript
   // Linia 203: po zapisie edycji kontenera
   const from = getFrom(route)
   router.push({
     path: GearRoutePath.ContainerDetailById(containerId),
     query: createNavigationQuery(undefined, from),
   })
   ```

3. **ContainerHeader.vue** - użyć parametru `from` do określenia celu nawigacji (jak wyżej)

**Uzasadnienie poprawki:**
- Użycie parametru `from` jest spójne z rozwiązaniem używanym w `ItemHeader.vue`
- Użytkownik zawsze wraca tam, skąd przyszedł (zachowanie zgodne z oczekiwaniami)
- Działa poprawnie niezależnie od źródła nawigacji
- Parametr `from` jest zachowywany podczas nawigacji po zapisie edycji

**Scenariusze po poprawce:**

1. **ContainersList → ContainerDetails**
   - Parametr `from`: `undefined` (domyślnie)
   - Przycisk "Wróć" → `ContainersList` ✅

2. **AllItemsPage → ContainerDetails**
   - Parametr `from`: `'all-items'` (ustawiany przez `AllItemsPage`)
   - Przycisk "Wróć" → `AllItemsPage` ✅

3. **AllItemsPage → ContainerDetails → Edit → Save → ContainerDetails**
   - Parametr `from`: `'all-items'` (zachowywany przez `ContainerFormPage`)
   - Po zapisie: nawigacja do `ContainerDetails` z `from=all-items`
   - Przycisk "Wróć" → `AllItemsPage` ✅

4. **ContainerDetails → Edit → Save → ContainerDetails**
   - Parametr `from`: `undefined` (domyślnie)
   - Po zapisie: nawigacja do `ContainerDetails` bez parametru `from`
   - Przycisk "Wróć" → `ContainersList` ✅

#### 3. PublicContainerHeader.vue

**Lokalizacja:** `src/modules/gear/components/PublicContainerHeader.vue`  
**Użycie:** Wyświetlany na stronach `PublicContainerDetailPage` i `SharedContainerDetailPage`  
**Metoda nawigacji:** Prop `backPath` lub emit `back`

**Logika nawigacji:**
```typescript
const handleBack = () => {
  if (props.backPath) {
    router.push(props.backPath)
  } else {
    emit('back')
  }
}
```

**Uzasadnienie:** Komponent przyjmuje opcjonalny prop `backPath`, który określa dokąd nawigować. Jeśli nie jest podany, emituje event `back`, który jest obsługiwany przez komponent rodzica.

**Scenariusze:**

1. **PublicContainers → PublicContainerDetail**
   - Prop `backPath`: `GearRoutePath.PublicContainers`
   - Przycisk "Wróć" → `PublicContainers` ✅

2. **SharedContainerDetail (przez token)**
   - Emit `back` → obsługiwany przez `SharedContainerDetailPage`
   - Przycisk "Wróć" → `PublicContainers` ✅

#### 4. PublicItemDetailPage.vue

**Lokalizacja:** `src/modules/gear/pages/PublicItemDetailPage.vue`  
**Użycie:** Strona szczegółów publicznego przedmiotu  
**Metoda nawigacji:** Explicit navigation do `PublicContainerDetailById`

**Logika nawigacji:**
```typescript
const handleBack = () => {
  router.push(GearRoutePath.PublicContainerDetailById(containerId))
}
```

**Uzasadnienie:** Zawsze nawiguje do szczegółów kontenera, z którego pochodzi przedmiot. Nie używa parametru `from`, ponieważ publiczne przedmioty są zawsze wyświetlane w kontekście kontenera.

**Scenariusze:**

1. **PublicContainers → PublicContainerDetail → PublicItemDetail**
   - Przycisk "Wróć" → `PublicContainerDetailById(containerId)` ✅

#### 5. ContainerShareTokensPage.vue

**Lokalizacja:** `src/modules/gear/pages/ContainerShareTokensPage.vue`  
**Użycie:** Strona zarządzania tokenami udostępniania kontenera  
**Metoda nawigacji:** Explicit navigation do `ContainerDetailById`

**Logika nawigacji:**
```typescript
const handleBack = () => {
  router.push(GearRoutePath.ContainerDetailById(containerId))
}
```

**Uzasadnienie:** Zawsze nawiguje z powrotem do szczegółów kontenera, z którego użytkownik przyszedł. Jest to strona pomocnicza, więc zawsze wraca do głównej strony kontenera.

**Scenariusze:**

1. **ContainerDetails → ContainerShareTokens**
   - Przycisk "Wróć" → `ContainerDetailById(containerId)` ✅

#### 6. ProfileEditPage.vue

**Lokalizacja:** `src/modules/user/pages/ProfileEditPage.vue`  
**Użycie:** Strona edycji profilu użytkownika  
**Metoda nawigacji:** Explicit navigation do `UserRoutePaths.profile`

**Logika nawigacji:**
```typescript
const handleCancel = () => {
  router.push(UserRoutePaths.profile)
}
```

**Uzasadnienie:** Zawsze nawiguje z powrotem do strony profilu użytkownika. Nie używa `router.back()`, ponieważ strona może być otwarta z różnych miejsc (np. z linku bezpośredniego).

**Scenariusze:**

1. **Profile → ProfileEdit**
   - Przycisk "Wróć" → `UserRoutePaths.profile` ✅

#### 7. TwoFactorSetupPage.vue

**Lokalizacja:** `src/modules/auth/pages/TwoFactorSetupPage.vue`  
**Użycie:** Strona konfiguracji 2FA  
**Metoda nawigacji:** `ButtonLink` do `SettingsRoutePaths.settings`

**Logika nawigacji:**
```vue
<ButtonLink variant="outline" :to="SettingsRoutePaths.settings">
  {{ t('common.back') }}
</ButtonLink>
```

**Uzasadnienie:** Używa `ButtonLink` zamiast funkcji nawigacji, ponieważ jest to prosty link do strony ustawień. Strona jest zawsze otwierana z ustawień, więc link jest bezpieczny.

**Scenariusze:**

1. **Settings → TwoFactorSetup**
   - Przycisk "Wróć" → `SettingsRoutePaths.settings` ✅

#### 8. CatalogueItemDetailPage.vue

**Lokalizacja:** `src/modules/gear/pages/catalogue/CatalogueItemDetailPage.vue`  
**Użycie:** Strona szczegółów przedmiotu z katalogu  
**Metoda nawigacji:** Explicit navigation do `CatalogueBrowser`

**Logika nawigacji:**
```typescript
const goBack = () => {
  router.push(GearRoutePath.CatalogueBrowser)
}
```

**Uzasadnienie:** Zawsze nawiguje z powrotem do przeglądarki katalogu. Strona jest zawsze otwierana z przeglądarki katalogu, więc explicit navigation jest bezpieczne.

**Scenariusze:**

1. **CatalogueBrowser → CatalogueItemDetail**
   - Przycisk "Wróć" → `CatalogueBrowser` ✅

## 🔧 Implementacja

### ItemHeader.vue

```typescript
const backTo = computed<string>(() => {
  const from = getFrom(route)
  if (from === 'all-items') {
    return GearRoutePath.AllItems
  }
  return GearRoutePath.ContainerDetailById(containerId)
})

const handleBack = () => {
  router.push(backTo.value)
}
```

### useNavigationReturn.ts

Funkcja `navigateBackAndClean()` zachowuje parametr `from` przy nawigacji do ItemDetails:

```typescript
async function navigateBackAndClean() {
  const returnToValue = returnTo.value
  const fromValue = from.value

  if (returnToValue === 'detail' && itemId) {
    // Preserve 'from' parameter when navigating back to ItemDetails
    // This ensures the back button in ItemHeader works correctly
    await router.push({
      path: GearRoutePath.ItemDetailById(containerId, itemId),
      query: createNavigationQuery(undefined, fromValue),
    })
  } else if (returnToValue === 'shopping') {
    await router.push(GearRoutePath.ShoppingPlanning)
  } else {
    await router.push({
      path: GearRoutePath.ContainerDetailById(containerId),
      query: {},
    })
  }
}
```

## 📊 Przepływ parametrów

### Scenariusz 1: ContainersList → ContainerDetails → ItemDetails

```
1. ContainersList
   ↓ (kliknięcie w kontener)
2. ContainerDetails
   ↓ (ItemsTable.navigateToItem() z from='container')
3. ItemDetails?from=container
   ↓ (przycisk "Wróć")
4. ContainerDetails ✅
```

### Scenariusz 2: ContainersList → ContainerDetails → ItemDetails → Edit → Save

```
1. ContainersList
   ↓
2. ContainerDetails
   ↓ (ItemsTable.navigateToItem() z from='container')
3. ItemDetails?from=container
   ↓ (kliknięcie "Edytuj" - handleEdit() z returnTo='detail', from='container')
4. ItemEdit?returnTo=detail&from=container
   ↓ (zapis - navigateBackAndClean() zachowuje from='container')
5. ItemDetails?from=container
   ↓ (przycisk "Wróć")
6. ContainerDetails ✅
```

### Scenariusz 3: AllItemsPage → ItemDetails

```
1. AllItemsPage
   ↓ (kliknięcie w przedmiot z from='all-items')
2. ItemDetails?from=all-items
   ↓ (przycisk "Wróć")
3. AllItemsPage ✅
```

### Scenariusz 4: AllItemsPage → ItemDetails → Edit → Save

```
1. AllItemsPage
   ↓
2. ItemDetails?from=all-items
   ↓ (kliknięcie "Edytuj" - handleEdit() z returnTo='detail', from='all-items')
3. ItemEdit?returnTo=detail&from=all-items
   ↓ (zapis - navigateBackAndClean() zachowuje from='all-items')
4. ItemDetails?from=all-items
   ↓ (przycisk "Wróć")
5. AllItemsPage ✅
```

### Scenariusz 5: AllItemsPage → ContainerDetails → Edit → Save

```
1. AllItemsPage
   ↓ (kliknięcie w kontener z from='all-items')
2. ContainerDetails?from=all-items
   ↓ (kliknięcie "Edytuj")
3. ContainerEdit
   ↓ (zapis - ContainerFormPage zachowuje from='all-items')
4. ContainerDetails?from=all-items
   ↓ (przycisk "Wróć")
5. AllItemsPage ✅
```

### Scenariusz 6: ContainersList → ContainerDetails → Edit → Save

```
1. ContainersList
   ↓ (kliknięcie w kontener)
2. ContainerDetails
   ↓ (kliknięcie "Edytuj")
3. ContainerEdit
   ↓ (zapis - ContainerFormPage bez parametru from)
4. ContainerDetails
   ↓ (przycisk "Wróć")
5. ContainersList ✅
```

## 🎓 Dlaczego nie `router.back()`?

### Problem z `router.back()`

`router.back()` polega na historii przeglądarki, która może być nieprzewidywalna:

1. **Programatyczna nawigacja** - gdy aplikacja programatycznie nawiguje (np. po zapisie), dodaje nowy wpis do historii, co może zmienić oczekiwane zachowanie `router.back()`

2. **Wielokrotne nawigacje** - jeśli użytkownik nawiguje między stronami wielokrotnie, historia może być skomplikowana i `router.back()` może nie prowadzić tam, gdzie oczekujemy

3. **Brak kontekstu** - `router.back()` nie wie, skąd użytkownik przyszedł w kontekście aplikacji, tylko gdzie był w historii przeglądarki

4. **Bezpośrednie linki** - jeśli użytkownik otworzy stronę przez bezpośredni link (np. z zakładki, emaila), `router.back()` może prowadzić poza aplikację

### Zalety parametru `from` i explicit navigation

1. **Przewidywalność** - zawsze wiemy, dokąd powinien prowadzić przycisk "Wróć"
2. **Kontekst aplikacji** - parametr `from` reprezentuje kontekst aplikacji, nie historię przeglądarki
3. **Niezależność od historii** - działa poprawnie niezależnie od tego, jak skomplikowana jest historia przeglądarki
4. **Spójność** - wszystkie scenariusze nawigacji działają tak samo
5. **Bezpieczeństwo** - explicit navigation zawsze prowadzi do poprawnego miejsca w aplikacji

## 🎯 Rekomendowane podejście do nawigacji "Wróć"

### Zasady ogólne

1. **Użyj parametru `from`** gdy strona może być otwarta z różnych miejsc w aplikacji
   - Przykład: `ItemHeader` - może być otwarty z `AllItemsPage` lub `ContainerDetailPage`

2. **Użyj explicit navigation** gdy strona jest zawsze otwarta z jednego miejsca lub gdy chcemy zawsze wracać do głównej strony
   - Przykład: `ContainerShareTokensPage` - zawsze wraca do `ContainerDetailPage`
   - Przykład: `ProfileEditPage` - zawsze wraca do `ProfilePage`

3. **Unikaj `router.back()`** gdy:
   - Strona może być otwarta z różnych miejsc
   - Strona może być otwarta przez bezpośredni link
   - Po zapisie/akcji następuje programatyczna nawigacja (dodaje wpis do historii)

4. **Możesz użyć `router.back()`** tylko gdy:
   - Strona jest zawsze otwarta z jednego miejsca
   - Nie ma programatycznej nawigacji po akcjach
   - Historia przeglądarki jest przewidywalna

### Proponowane poprawki

#### 1. ContainerHeader.vue - zmiana na użycie parametru `from` (PRIORYTET)

**Obecne zachowanie:**
```typescript
const handleBack = () => {
  router.push(GearRoutePath.Containers)
}
```

**Proponowane zachowanie:**
```typescript
import { useRoute } from 'vue-router'
import { getFrom } from '../utils/navigationParams'
import { GearRoutePath } from '../routes'

const route = useRoute()

const backTo = computed<string>(() => {
  const from = getFrom(route)
  if (from === 'all-items') {
    return GearRoutePath.AllItems
  }
  // Domyślnie wracamy do ContainersList
  return GearRoutePath.Containers
})

const handleBack = () => {
  router.push(backTo.value)
}
```

**Uzasadnienie:**
- `ContainerDetailPage` może być otwarty z różnych miejsc:
  - `ContainersList` (główna lista) → powrót do `ContainersList` ✅
  - `AllItemsPage` (kliknięcie w kontener) → powrót do `AllItemsPage` ✅ (obecnie ❌)
  - `ContainerFormPage` (po zapisie edycji) → powrót do poprzedniej strony ✅
  - `ContainerShareTokensPage` (po zarządzaniu tokenami) → powrót do `ContainerDetailPage` ✅
  - Bezpośrednie linki (zakładki, emaile) → powrót do `ContainersList` ✅
- Użycie parametru `from` jest spójne z rozwiązaniem używanym w `ItemHeader.vue`
- Użytkownik zawsze wraca tam, skąd przyszedł (zachowanie zgodne z oczekiwaniami)
- Parametr `from` jest zachowywany podczas nawigacji po zapisie edycji

**Wymagane zmiany w innych plikach:**

1. **AllItemsPage.vue** - dodać parametr `from='all-items'` przy nawigacji do `ContainerDetailPage`:
   - Linia 355: gdy klikamy na kontener w kolumnie `name`
   - Linia 369: gdy klikamy na kontener w kolumnie `container`

2. **ContainerFormPage.vue** - zachować parametr `from` przy nawigacji po zapisie:
   - Linia 203: po zapisie edycji kontenera

**Status:** ⚠️ **Wymaga implementacji** - zidentyfikowany problem w scenariuszu użycia

#### 2. PublicContainerHeader.vue - już dobrze zaimplementowane

**Obecne zachowanie:** Używa prop `backPath` lub emit `back` ✅

**Status:** Nie wymaga zmian - elastyczne podejście z prop/emit jest odpowiednie dla komponentu używanego w różnych kontekstach.

#### 3. Inne komponenty - sprawdzenie spójności

Wszystkie pozostałe komponenty używają explicit navigation, co jest poprawne:
- ✅ `PublicItemDetailPage` - explicit navigation do `PublicContainerDetailById`
- ✅ `ContainerShareTokensPage` - explicit navigation do `ContainerDetailById`
- ✅ `ProfileEditPage` - explicit navigation do `UserRoutePaths.profile`
- ✅ `TwoFactorSetupPage` - `ButtonLink` do `SettingsRoutePaths.settings`
- ✅ `CatalogueItemDetailPage` - explicit navigation do `CatalogueBrowser`

## ✅ Kryteria akceptacji

- ✅ Przycisk "Wróć" w `ItemHeader` nawiguje poprawnie we wszystkich scenariuszach
- ✅ Parametr `from` jest zachowywany podczas nawigacji po zapisie edycji
- ✅ `navigateBackAndClean()` zachowuje parametr `from` przy nawigacji do ItemDetails
- ✅ Wszystkie scenariusze nawigacji działają poprawnie
- ⚠️ Przycisk "Wróć" w `ContainerHeader` nawiguje poprawnie we wszystkich scenariuszach (wymaga implementacji)
- ⚠️ Parametr `from` jest przekazywany z `AllItemsPage` do `ContainerDetailPage` (wymaga implementacji)
- ⚠️ Parametr `from` jest zachowywany przez `ContainerFormPage` przy nawigacji po zapisie (wymaga implementacji)

## 📝 Pliki związane

- `src/modules/gear/components/ItemHeader.vue` - implementacja przycisku "Wróć" ✅
- `src/modules/gear/components/ContainerHeader.vue` - implementacja przycisku "Wróć" ⚠️ (wymaga poprawki - użycie parametru `from`)
- `src/modules/gear/pages/AllItemsPage.vue` - nawigacja do `ContainerDetailPage` ⚠️ (wymaga dodania parametru `from='all-items'`)
- `src/modules/gear/pages/ContainerFormPage.vue` - nawigacja po zapisie ⚠️ (wymaga zachowania parametru `from`)
- `src/modules/gear/composables/useNavigationReturn.ts` - logika nawigacji po zapisie
- `src/modules/gear/utils/navigationParams.ts` - helper functions do zarządzania parametrami

## 📌 Uwagi i przypadki użycia

### Zidentyfikowany problem

**Scenariusz:**
1. Użytkownik otwiera `/gear/items` (AllItemsPage)
2. Wybiera na liście kontener → otwiera się `/gear/01KBYM0E0D3STQ8Z279HMDQWKB` (ContainerDetailPage)
3. Klika "Edytuj" → otwiera się `/gear/01KBYM0E0D3STQ8Z279HMDQWKB/edit` (ContainerFormPage)
4. Klika "Zapisz" → otwiera się znowu `/gear/01KBYM0E0D3STQ8Z279HMDQWKB` (ContainerDetailPage)
5. Klika "Wstecz" → otwiera się `/gear` (ContainersList) ❌
   - **Oczekiwane:** `/gear/items` (AllItemsPage) ✅

**Przyczyna:**
- `ContainerHeader.vue` zawsze nawiguje do `GearRoutePath.Containers` niezależnie od źródła nawigacji
- `AllItemsPage.vue` nie przekazuje parametru `from='all-items'` przy nawigacji do `ContainerDetailPage`
- `ContainerFormPage.vue` nie zachowuje parametru `from` przy nawigacji po zapisie

**Rozwiązanie:**
Użycie parametru `from` podobnie jak w `ItemHeader.vue`:
1. `AllItemsPage.vue` - dodać parametr `from='all-items'` przy nawigacji do `ContainerDetailPage`
2. `ContainerFormPage.vue` - zachować parametr `from` przy nawigacji po zapisie
3. `ContainerHeader.vue` - użyć parametru `from` do określenia celu nawigacji

### Inne przypadki użycia do rozważenia

1. **Nawigacja z ContainerShareTokensPage:**
   - Obecnie: `ContainerShareTokensPage` zawsze wraca do `ContainerDetailPage`
   - Czy powinien zachowywać parametr `from`? → **Nie**, ponieważ jest to strona pomocnicza, zawsze wraca do kontenera

2. **Nawigacja z bezpośrednich linków:**
   - Obecnie: bez parametru `from` → powrót do `ContainersList`
   - Czy to jest poprawne? → **Tak**, domyślne zachowanie jest intuicyjne

3. **Nawigacja z ContainersList:**
   - Obecnie: bez parametru `from` → powrót do `ContainersList`
   - Czy to jest poprawne? → **Tak**, zgodne z oczekiwaniami

## 🔧 Plan implementacji

### Krok 1: Aktualizacja `AllItemsPage.vue`
- Dodać parametr `from='all-items'` przy nawigacji do `ContainerDetailPage` (linie 355 i 369)
- Użyć `createNavigationQuery(undefined, 'all-items')` podobnie jak przy nawigacji do `ItemDetailPage`

### Krok 2: Aktualizacja `ContainerFormPage.vue`
- Pobrać parametr `from` z route przed nawigacją po zapisie
- Przekazać parametr `from` w query string przy nawigacji do `ContainerDetailPage`
- Użyć `createNavigationQuery(undefined, from)` do zachowania parametru

### Krok 3: Aktualizacja `ContainerHeader.vue`
- Dodać import `useRoute` i `getFrom` z `navigationParams.ts`
- Utworzyć computed `backTo` podobnie jak w `ItemHeader.vue`
- Zmienić `handleBack` aby używał `backTo.value` zamiast hardcoded `GearRoutePath.Containers`

### Krok 4: Testowanie
- Przetestować scenariusz: AllItemsPage → ContainerDetails → Edit → Save → Back
- Przetestować scenariusz: ContainersList → ContainerDetails → Edit → Save → Back
- Przetestować scenariusz: AllItemsPage → ContainerDetails → Back
- Przetestować scenariusz: ContainersList → ContainerDetails → Back

## 🔗 Powiązane dokumenty

- [FEATURE-026: Refaktoryzacja systemu query parametrów](./2026-03-01--feature-026-query-params-refactoring.md)
- [Analiza query parametrów](../reviews/2026-07-09--query-params-analysis.md)

