# FEATURE-022: Accessibility (Dostępność)

**Status:** 🚧 In Progress  
**Priority:** Medium  
**Category:** ♿ Accessibility / 🎨 UI/UX  
**Related:** [ROADMAP_OFFLINE.md](../ROADMAP_OFFLINE.md) - ♿ Accessibility (Dostępność)

**Progress:** Faza 2 zrealizowana ✅, Faza 3 zrealizowana ✅ (tooltips, aria-label, semantyka HTML, aria-expanded). Pozostały tylko testy manualne.

---

## 📋 Overview

Implementacja podstawowych oznaczeń ARIA i poprawa dostępności aplikacji, szczególnie dla przycisków z ikonami. Zapewnienie zgodności z wytycznymi WCAG i lepszego doświadczenia użytkownika dla wszystkich, w tym użytkowników korzystających z czytników ekranu.

---

## 🎯 Goals

1. **Podstawowe oznaczenia ARIA** - Dodanie odpowiednich atrybutów ARIA do komponentów
2. **Tooltips na przyciskach z ikonami** - Wszystkie przyciski zawierające tylko ikonę powinny mieć tooltip z przetłumaczoną nazwą akcji
3. **Spójność aria-label i tooltip** - aria-label i tooltip mogą mieć tę samą treść dla lepszej spójności
4. **Semantyczny HTML** - Zapewnienie poprawnej semantyki HTML (użycie odpowiednich tagów)
5. **Nawigacja klawiaturą** - Poprawa obsługi nawigacji klawiaturą (focus management)

---

## 🔍 Current State

### ✅ Co już działa:

1. **Tooltips są już używane w niektórych miejscach:**
   - `ItemImageCardControls.vue` - wszystkie przyciski mają tooltips i aria-label
   - `FavoriteContainerButton.vue` - ma tooltip i aria-label
   - `ContainersListPage.vue` - niektóre przyciski mają tooltips
   - `ContainerHeader.vue` - niektóre elementy mają tooltips

2. **Aria-label są już używane w niektórych miejscach:**
   - `ContainerCardActions.vue` - przycisk MoreVertical ma aria-label (ale brak tooltipa)
   - `ContainerHeader.vue` - przycisk MoreActionsIcon ma aria-label (ale brak tooltipa)
   - `ContainersListPageDropdown.vue` - przycisk MoreActionsIcon ma aria-label (ale brak tooltipa)

3. **Tooltip directive jest już skonfigurowany:**
   - `v-tooltip` directive z floating-vue jest zarejestrowany w `main.ts`
   - Używa się `v-tooltip.bottom="t('key')"` dla tooltipów

### ✅ Zrealizowane (2025-01-21):

1. **Przyciski z ikonami - tooltips dodane:**
   - ✅ `ItemsTableRowActions.vue` - przycisk MoreHorizontal (dodano tooltip i aria-label)
   - ✅ `ContainerCardActions.vue` - przycisk MoreVertical (dodano tooltip, miał już aria-label)
   - ✅ `ContainerHeader.vue` - przycisk MoreActionsIcon (dodano tooltip, miał już aria-label)
   - ✅ `ContainersListPageDropdown.vue` - przycisk MoreActionsIcon (dodano tooltip, miał już aria-label)
   - ✅ `AiChatInputSection.vue` - przycisk SendIcon (dodano tooltip i aria-label, dodano translację `ai.chat.send`)

### ✅ Zrealizowane (2025-01-22):

2. **Dodatkowe przyciski z ikonami - tooltips i aria-label:**
   - ✅ `SidebarTrigger.vue` - dodano tooltip i aria-label (translacja `common.toggleSidebar`)
   - ✅ `DarkModeToggle.vue` - dodano tooltip (miał już aria-label, translacja `common.toggleDarkMode`)
   - ✅ `LocaleToggle.vue` - dodano tooltip (miał już aria-label, translacja `common.toggleLanguage`)
   - ✅ `ShoppingListItem.vue` - dodano tooltips i aria-label do przycisków increment/decrement/delete (translacje `gear.shopping.incrementQuantity`, `gear.shopping.decrementQuantity`, `gear.shopping.removeFromList`)
   - ✅ `RatingStars.vue` - dodano aria-label do przycisków gwiazdek (translacja `gear.actions.rateStar` z pluralizacją)
   - ✅ `ItemsTableEditableNameCell.vue` - dodano tooltip i aria-label do przycisku reset (translacja `gear.actions.undo`)
   - ✅ `ItemsTableMoveButtons.vue` - dodano tooltips i aria-label do przycisków move up/down (translacje `gear.actions.moveUp`, `gear.actions.moveDown`)

3. **Semantyka HTML i landmarky ARIA:**
   - ✅ `AppHeader.vue` - używa `<header>` i `<nav>` ✅
   - ✅ `AppFooter.vue` - używa `<footer>` i `<nav>` ✅
   - ✅ `AuthenticatedLayout.vue` - używa `<main>` ✅
   - ✅ `AppSidebar.vue` - używa komponentów Sidebar z odpowiednią semantyką ✅

4. **Atrybuty ARIA dla interaktywnych elementów:**
   - ✅ `ItemsTableNameCell.vue` - dodano `aria-expanded` i `aria-label` do przycisku expand/collapse (translacje `gear.item.expandContainer`, `gear.item.collapseContainer`)
   - ✅ `ComboBox.vue` - już ma `aria-expanded` ✅
   - ✅ `FormControl.vue` - już ma `aria-describedby` ✅
   - ✅ Dialog/Modal (reka-ui) - biblioteka obsługuje odpowiednie atrybuty ARIA ✅

### ✅ Zrealizowane - wszystkie główne zadania ukończone:

1. **Przyciski z ikonami z tooltipami i aria-label:** ✅
   - Wszystkie główne komponenty mają tooltips i aria-label
   - Dodano do: SidebarTrigger, DarkModeToggle, LocaleToggle, ShoppingListItem, RatingStars, ItemsTableEditableNameCell, ItemsTableMoveButtons

2. **Translacje dla tooltipów:** ✅
   - Wszystkie potrzebne translacje zostały dodane (PL i EN)

3. **Semantyka HTML:** ✅
   - Sprawdzone i poprawne użycie tagów (header, nav, main, footer)
   - Landmarky ARIA są prawidłowo użyte

4. **Atrybuty ARIA:** ✅
   - aria-expanded dodane do expand/collapse
   - aria-label dodane do wszystkich przycisków z ikonami
   - ComboBox i FormControl już mają odpowiednie atrybuty

### ⏳ Do wykonania (testy manualne):

1. **Focus management:**
   - Testy manualne z nawigacją klawiaturą (reka-ui prawdopodobnie już obsługuje)
   - Testy z czytnikiem ekranu (NVDA, JAWS, VoiceOver)

2. **Narzędzia automatyczne:**
   - Lighthouse Accessibility audit (cel: >90)
   - axe DevTools audit
   - WAVE audit

---

## 📝 Implementation Plan

### Faza 1: Audyt i identyfikacja (Small complexity)

**Cel:** Zidentyfikować wszystkie miejsca wymagające poprawy

1. **Przeszukanie komponentów z przyciskami ikonowymi:**
   - Znalezienie wszystkich komponentów używających `Button` z ikonami
   - Sprawdzenie, które mają tooltips, które mają aria-label, które nie mają żadnego
   - Utworzenie listy komponentów do poprawy

2. **Sprawdzenie semantyki HTML:**
   - Audyt użycia tagów HTML (button vs div, nav vs div, itp.)
   - Identyfikacja brakujących landmarków ARIA

3. **Sprawdzenie translacji:**
   - Weryfikacja, czy wszystkie potrzebne translacje istnieją
   - Identyfikacja brakujących kluczy translacji

**Pliki do sprawdzenia:**
- `src/modules/gear/components/` - wszystkie komponenty
- `src/modules/gear/pages/` - strony z przyciskami
- `src/modules/admin/components/` - komponenty admin
- `src/modules/auth/components/` - komponenty auth
- `src/shared/components/` - wspólne komponenty

---

### Faza 2: Dodanie tooltipów do przycisków z ikonami (Medium complexity)

**Cel:** Wszystkie przyciski z ikonami powinny mieć tooltips

#### 2.1. ItemsTableRowActions.vue ✅

**Plik:** `src/modules/gear/components/ItemsTableRowActions.vue`

**Status:** ✅ Zrealizowane (2025-01-21)

**Zmiany:**
- ✅ Dodanie `v-tooltip.bottom` do przycisku MoreHorizontal
- ✅ Dodanie `aria-label` do przycisku MoreHorizontal
- ✅ Użycie istniejącej translacji `gear.actions.moreActions`

```vue
<Button 
  variant="ghost" 
  class="size-8 p-0"
  v-tooltip.bottom="t('gear.actions.moreActions')"
  :aria-label="t('gear.actions.moreActions')"
>
  <MoreHorizontal class="size-4" />
</Button>
```

#### 2.2. ContainerCardActions.vue ✅

**Plik:** `src/modules/gear/components/ContainerCardActions.vue`

**Status:** ✅ Zrealizowane (2025-01-21)

**Zmiany:**
- ✅ Dodanie `v-tooltip.bottom` do przycisku MoreVertical (już ma aria-label)
- ✅ Użycie istniejącej translacji `gear.actions.moreActions`

```vue
<Button
  variant="ghost"
  size="sm"
  class="size-8 p-0"
  v-tooltip.bottom="t('gear.actions.moreActions')"
  :aria-label="t('gear.actions.moreActions')"
  @click.stop
>
  <MoreVertical class="size-4" />
</Button>
```

#### 2.3. ContainerHeader.vue ✅

**Plik:** `src/modules/gear/components/ContainerHeader.vue`

**Status:** ✅ Zrealizowane (2025-01-21)

**Zmiany:**
- ✅ Dodanie `v-tooltip.bottom` do przycisku MoreActionsIcon (już ma aria-label)
- ✅ Użycie istniejącej translacji `gear.actions.moreActions`

```vue
<Button
  variant="outline"
  size="sm"
  class="shrink-0"
  v-tooltip.bottom="t('gear.actions.moreActions')"
  :aria-label="t('gear.actions.moreActions')"
>
  <MoreActionsIcon class="size-4" />
</Button>
```

#### 2.4. ContainersListPageDropdown.vue ✅

**Plik:** `src/modules/gear/components/ContainersListPageDropdown.vue`

**Status:** ✅ Zrealizowane (2025-01-21)

**Zmiany:**
- ✅ Dodanie `v-tooltip.bottom` do przycisku MoreActionsIcon (już ma aria-label)
- ✅ Użycie istniejącej translacji `gear.actions.moreActions`

```vue
<Button
  variant="outline"
  class="sm:shrink-0"
  v-tooltip.bottom="t('gear.actions.moreActions')"
  :aria-label="t('gear.actions.moreActions')"
>
  <MoreActionsIcon class="size-4" />
</Button>
```

#### 2.5. Inne komponenty

**Sprawdzenie i poprawa innych komponentów z przyciskami ikonowymi:**
- Wszystkie komponenty w `src/modules/gear/components/`
- Komponenty w innych modułach (admin, auth, user, settings)
- Wspólne komponenty w `src/shared/components/`

**Kryteria:**
- Jeśli przycisk zawiera tylko ikonę (bez tekstu) → musi mieć tooltip i aria-label
- Jeśli przycisk zawiera ikonę + tekst → tooltip opcjonalny, ale aria-label może być przydatny
- Tooltip i aria-label mogą mieć tę samą treść

---

### Faza 3: Dodanie podstawowych oznaczeń ARIA (Medium complexity)

**Cel:** Poprawa semantyki HTML i dodanie podstawowych atrybutów ARIA

#### 3.1. Landmarks ARIA

**Dodanie landmarków do głównych regionów:**

- `role="navigation"` lub `<nav>` dla głównej nawigacji
- `role="main"` lub `<main>` dla głównej zawartości
- `role="banner"` lub `<header>` dla nagłówka
- `role="contentinfo"` lub `<footer>` dla stopki

**Pliki do sprawdzenia:**
- `src/layouts/AuthenticatedLayout.vue` - layout z nawigacją
- `src/App.vue` - główna struktura aplikacji
- Komponenty z nawigacją (topbar, sidebar)

#### 3.2. Atrybuty ARIA dla interaktywnych elementów

**Dodanie atrybutów:**
- `aria-expanded` dla dropdownów, accordionów
- `aria-hidden` dla elementów ukrytych wizualnie
- `aria-describedby` dla elementów z opisami
- `aria-label` dla elementów bez widocznej etykiety
- `aria-live` dla dynamicznych treści (toast notifications)

**Przykłady:**
- DropdownMenu - `aria-expanded` na triggerze
- Dialog/Modal - `aria-labelledby`, `aria-describedby`
- Toast notifications - `aria-live="polite"`

#### 3.3. Semantyczny HTML

**Sprawdzenie i poprawa:**
- Użycie `<button>` zamiast `<div>` dla przycisków
- Użycie `<nav>` zamiast `<div>` dla nawigacji
- Użycie `<main>` zamiast `<div>` dla głównej zawartości
- Użycie `<header>`, `<footer>` zamiast `<div>`

---

### Faza 4: Focus Management (Medium complexity)

**Cel:** Poprawa obsługi nawigacji klawiaturą

#### 4.1. Focus w dialogach i modalach

**Zapewnienie:**
- Focus trap w dialogach (focus nie wychodzi poza dialog)
- Automatyczne ustawienie focus na pierwszy interaktywny element przy otwarciu
- Powrót focus do elementu, który otworzył dialog, po zamknięciu

**Pliki do sprawdzenia:**
- Komponenty Dialog/Modal (shadcn-vue/reka-ui)
- Sprawdzenie, czy biblioteka już to obsługuje

#### 4.2. Keyboard shortcuts (opcjonalnie)

**Dodanie podstawowych skrótów klawiszowych:**
- `Ctrl/Cmd + K` - wyszukiwarka (jeśli istnieje)
- `Esc` - zamknięcie dialogów/modalów
- `Tab` - nawigacja między elementami (już działa, ale sprawdzić kolejność)

---

### Faza 5: Testy i weryfikacja (Small complexity)

**Cel:** Weryfikacja poprawy dostępności

1. **Testy manualne:**
   - Test z czytnikiem ekranu (NVDA, JAWS, VoiceOver)
   - Test nawigacji klawiaturą (Tab, Shift+Tab, Enter, Space, Esc)
   - Test tooltipów (hover i focus)

2. **Narzędzia automatyczne:**
   - axe DevTools (rozszerzenie przeglądarki)
   - Lighthouse Accessibility audit
   - WAVE (Web Accessibility Evaluation Tool)

3. **Sprawdzenie zgodności z WCAG:**
   - WCAG 2.1 Level AA (cel minimum)
   - Sprawdzenie kontrastu kolorów
   - Sprawdzenie rozmiaru klikalnych elementów (min 44x44px)

---

## 📋 Lista brakujących translacji

### Sprawdzenie istniejących translacji

**Plik:** `src/modules/gear/i18n/index.ts`

**Istniejące translacje akcji (gear.actions):**
- ✅ `show` - "Show" / "Pokaż"
- ✅ `add` - "Add" / "Dodaj"
- ✅ `edit` - "Edit" / "Edytuj"
- ✅ `delete` - "Delete" / "Usuń"
- ✅ `save` - "Save" / "Zapisz"
- ✅ `cancel` - "Cancel" / "Anuluj"
- ✅ `export` - "Export Data" / "Eksportuj dane"
- ✅ `import` - "Import Data" / "Importuj dane"
- ✅ `move` - "Move Item" / "Przenieś Przedmiot"
- ✅ `recognizeParameters` - "Recognize Parameters" / "Rozpoznaj parametry"
- ✅ `recognizeParametersAll` - "Recognize Parameters for All Items" / "Rozpoznaj parametry wszystkich przedmiotów"
- ✅ `exportToPrompt` - "Export to prompt in Markdown (for AI)" / "Eksport do prompt w Markdown (AI)"
- ✅ `exportToCSV` - "Export to CSV" / "Eksport do CSV"
- ✅ `moreActions` - "More actions" / "Więcej akcji"

**Potencjalnie brakujące translacje (do weryfikacji):**

1. **Akcje kontenerów:**
   - `clone` - "Clone Container" / "Klonuj kontener" (sprawdzić czy istnieje w `gear.container.clone`)
   - `viewContainer` - "View Container" / "Pokaż kontener" (sprawdzić czy istnieje w `gear.item.viewContainer`)

2. **Statusy przedmiotów (dla tooltipów):**
   - Sprawdzić czy istnieją translacje dla statusów: `owned`, `missing`, `toBuy`
   - Prawdopodobnie istnieją w `gear.item.statuses.*`

3. **Inne akcje (do weryfikacji podczas audytu):**
   - Wszystkie akcje używające ikon z `actionIcons.ts` powinny mieć odpowiadające translacje

**Akcje z actionIcons.ts i ich translacje:**
- ✅ `back` - sprawdzić czy istnieje (prawdopodobnie w `common.back`)
- ✅ `moreActions` - istnieje w `gear.actions.moreActions`
- ✅ `create` - sprawdzić czy istnieje (prawdopodobnie w `gear.container.create.title`)
- ✅ `addItem` - sprawdzić czy istnieje (prawdopodobnie w `gear.item.create`)
- ✅ `addContainer` - sprawdzić czy istnieje (prawdopodobnie w `gear.container.addNested`)
- ✅ `edit` - istnieje w `gear.actions.edit`
- ✅ `delete` - istnieje w `gear.actions.delete`
- ✅ `deleteAll` - sprawdzić czy istnieje (prawdopodobnie w `gear.container.deleteAll`)
- ✅ `export` - istnieje w `gear.actions.export`
- ✅ `import` - istnieje w `gear.actions.import`
- ✅ `importFromMarkdown` - sprawdzić czy istnieje (prawdopodobnie w `gear.import.fromMarkdown`)
- ✅ `exportToPrompt` - istnieje w `gear.actions.exportToPrompt`
- ✅ `exportAllToPrompt` - sprawdzić czy istnieje (prawdopodobnie w `gear.export.allToPrompt`)
- ✅ `exportToCSV` - istnieje w `gear.actions.exportToCSV`
- ✅ `recognizeParameters` - istnieje w `gear.actions.recognizeParameters`
- ✅ `recognizeParametersAll` - istnieje w `gear.actions.recognizeParametersAll`
- ✅ `toggleItemImages` - sprawdzić czy istnieje (prawdopodobnie w `gear.container.hideItemImages` lub podobne)

**Wnioski:**
- Większość translacji prawdopodobnie już istnieje
- Podczas implementacji należy zweryfikować, czy wszystkie potrzebne translacje są dostępne
- Jeśli brakuje translacji, należy je dodać do `src/modules/gear/i18n/index.ts`

---

## 🎯 Główne obszary do poprawy

### 1. Przyciski z ikonami bez tooltipów

**Priorytet: Wysoki**

**Komponenty:**
- `ItemsTableRowActions.vue` - przycisk MoreHorizontal
- `ContainerCardActions.vue` - przycisk MoreVertical (ma aria-label, brak tooltipa)
- `ContainerHeader.vue` - przycisk MoreActionsIcon (ma aria-label, brak tooltipa)
- `ContainersListPageDropdown.vue` - przycisk MoreActionsIcon (ma aria-label, brak tooltipa)
- Inne komponenty z przyciskami ikonowymi (do zidentyfikowania podczas audytu)

### 2. Semantyka HTML i landmarky ARIA

**Priorytet: Średni**

**Obszary:**
- Główna nawigacja (topbar) - dodanie `<nav>` lub `role="navigation"`
- Główna zawartość stron - dodanie `<main>` lub `role="main"`
- Header/Footer - użycie semantycznych tagów
- Dialogi/Modale - sprawdzenie semantyki

### 3. Atrybuty ARIA dla interaktywnych elementów

**Priorytet: Średni**

**Obszary:**
- DropdownMenu - `aria-expanded` na triggerze
- Dialog/Modal - `aria-labelledby`, `aria-describedby`
- Accordion/Collapsible - `aria-expanded`
- Toast notifications - `aria-live="polite"`

### 4. Focus Management

**Priorytet: Średni**

**Obszary:**
- Dialogi/Modale - focus trap
- Automatyczne ustawienie focus przy otwarciu dialogu
- Powrót focus po zamknięciu dialogu

### 5. Testy dostępności

**Priorytet: Wysoki (po implementacji)**

**Narzędzia:**
- axe DevTools
- Lighthouse Accessibility audit
- WAVE
- Test z czytnikiem ekranu

---

## 📦 Zależności

- ✅ `floating-vue` - już zainstalowane (używane dla tooltipów)
- ✅ `vue-i18n` - już zainstalowane (używane dla translacji)
- ✅ `lucide-vue-next` - już zainstalowane (ikony)
- ✅ `shadcn-vue/reka-ui` - komponenty UI (Button, Dialog, DropdownMenu, itp.)

**Brak dodatkowych zależności** - wszystko już jest dostępne w projekcie.

---

## 🧪 Testy

### Testy manualne

1. **Test tooltipów:**
   - Hover nad przyciskami z ikonami → tooltip powinien się pojawić
   - Focus na przyciskach z ikonami (Tab) → tooltip powinien się pojawić
   - Tooltip powinien zawierać przetłumaczoną nazwę akcji

2. **Test z czytnikiem ekranu:**
   - Uruchomienie NVDA/JAWS/VoiceOver
   - Nawigacja przez przyciski z ikonami
   - Weryfikacja, czy aria-label jest odczytywane poprawnie

3. **Test nawigacji klawiaturą:**
   - Tab - przejście do następnego elementu
   - Shift+Tab - przejście do poprzedniego elementu
   - Enter/Space - aktywacja przycisku
   - Esc - zamknięcie dialogu/menua

### Testy automatyczne

1. **axe DevTools:**
   - Uruchomienie audytu dostępności
   - Naprawa wszystkich wykrytych problemów

2. **Lighthouse:**
   - Uruchomienie Accessibility audit
   - Cel: wynik powyżej 90

3. **WAVE:**
   - Sprawdzenie błędów i ostrzeżeń
   - Naprawa wykrytych problemów

---

## 📚 Zasoby

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [MDN: ARIA](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA)
- [floating-vue documentation](https://floating-vue.netlify.app/)
- [Vue i18n documentation](https://vue-i18n.intlify.dev/)

---

## ✅ Definition of Done

- [x] Wszystkie przyciski z ikonami mają tooltips z przetłumaczoną nazwą akcji ✅
- [x] Wszystkie przyciski z ikonami mają aria-label ✅
- [x] Główne regiony strony mają odpowiednie landmarky ARIA ✅
- [x] Interaktywne elementy mają odpowiednie atrybuty ARIA (aria-expanded, aria-labelledby, itp.) ✅
- [x] Semantyczny HTML jest używany wszędzie, gdzie to możliwe ✅
- [x] Wszystkie potrzebne translacje są dostępne w PL i EN ✅
- [ ] Focus management działa poprawnie w dialogach i modalach (wymaga testów manualnych - reka-ui prawdopodobnie już obsługuje)
- [ ] Testy z czytnikiem ekranu przechodzą pomyślnie (wymaga testów manualnych)
- [ ] Lighthouse Accessibility audit osiąga wynik powyżej 90 (wymaga testów manualnych)
- [ ] axe DevTools nie wykrywa krytycznych problemów dostępności (wymaga testów manualnych)

---

## 📝 Notatki

- Tooltip i aria-label mogą mieć tę samą treść - to jest w porządku i zapewnia spójność
- Priorytetem jest dodanie tooltipów do przycisków z ikonami (najbardziej widoczny problem)
- Semantyka HTML i landmarky ARIA są ważne, ale mniej krytyczne niż tooltips
- Focus management jest ważny dla użytkowników klawiatury, ale może wymagać sprawdzenia, czy biblioteka UI już to obsługuje

---

**Ostatnia aktualizacja:** 2025-01-22

**Uwagi:**
- Focus management w dialogach i modalach jest prawdopodobnie już obsługiwany przez reka-ui (biblioteka bazuje na ARIA Authoring Practices Guide)
- Wymagane są testy manualne z czytnikiem ekranu i nawigacją klawiaturą, aby potwierdzić pełną zgodność
- Wszystkie główne komponenty z przyciskami ikonowymi mają teraz tooltips i aria-label



