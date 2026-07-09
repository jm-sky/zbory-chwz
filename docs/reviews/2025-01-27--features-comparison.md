# Zestawienie funkcjonalności aplikacji

> 📋 **Zobacz też:**
> - [ROADMAP.md](./ROADMAP.md) - funkcjonalności front-end only (localStorage)
> - [ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md) - funkcjonalności wymagające backendu/DB/auth

Legenda:
- **[=]** – funkcjonalność pokrywa się z LighterPack  
- **[≠]** – funkcjonalność jest, ale działa inaczej niż w LighterPack  
- **[+]** – nowość w Waszej aplikacji (LighterPack tego nie ma)  
- **[→]** – funkcjonalność planowana  
- **[✓]** – funkcjonalność zaimplementowana (gotowa)  
- **[🔐]** – wymaga backendu/DB/auth (zobacz [ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md))

---

## 1. Struktura danych
- **Hierarchiczne kontenery (kontener w kontenerze)** — **[+]** **[✓]**
- **Lista / kontener główny** — **[≠]** **[✓]** (LP ma „lists", ale bez hierarchii)  
- **Przedmioty (items) z wagą, ilością, opisem, ceną** — **[=]** **[✓]**

## 2. Waga / jednostki
- **Automatyczne sumowanie wag kontenera i podkontenerów** — **[≠]** **[✓]** (rekurencyjne)  
- **Wykresy wagowe** — **[=]** **[✓]**  
- **Jednostki: kg / g** — **[=]** **[✓]**  
- **Jednostki: lb / oz** — **[✓]** (zaimplementowane)

## 3. Ceny / waluta
- **Cena produktu** — **[=]** **[✓]**  
- **Waluta per kontener + domyślna waluta użytkownika** — **[✓]** **[🔐]** (localStorage + synchronizacja z backendem zaimplementowana)

## 4. Notatki i opisy
- **Notatki tekstowe** — **[=]** **[✓]**  
- **Markdown w notatkach / opisach list i przedmiotów** — **[→]** (planowane)  
- **Eksport do Markdown** — **[+]** **[✓]**  
- **Import z Markdown** — **[+]** **[✓]**

## 5. Zarządzanie elementami
- **Kopiowanie / klonowanie kontenerów** — **[✓]** (front-end, localStorage)  
- **Globalny katalog itemów** — **[✓]** (lista wszystkich przedmiotów, front-end z localStorage)  
- **Autocomplete przy dodawaniu itemu do kontenera** — **[✓]** (front-end z localStorage)  
- **Linkowanie przedmiotów (zmiana w jednym → zmiana w wielu listach)** — **[+]** **[✓]** **[🔐]** (zaimplementowane)  
- **Typy przedmiotów: worn / consumable** — **[✓]** (front-end)

## 6. Udostępnianie i widoczność
- **Publiczny link do listy/kontenera** — **[✓]** **[🔐]**  
- **Poziomy widoczności: publiczna / niepubliczna / prywatna** — **[+]** **[✓]** **[🔐]**  
- **Galeria publiczna list/kontenerów** — **[+]** **[✓]** **[🔐]**  
- **Ocenianie (gwiazdki)** — **[+]** **[✓]** **[🔐]** (zaimplementowane)  
- **Komentarze** — **[+]** **[→]** **[🔐]** (planowane)

## 7. Przeglądarki
- **Przeglądarka kontenerów** — **[+]** **[✓]** (pokazuje drzewo kontenerów i zawartość) - front-end  
- **Przeglądarka przedmiotów (globalny katalog)** — **[+]** **[✓]** (front-end z localStorage)  
- **Dodawanie itemu do kontenera przez autocomplete z globalnego katalogu** — **[✓]** (front-end)  

## 8. UI / UX
- **Nowoczesny wygląd, lepszy UI/UX niż LP** — **[+]** **[✓]**  
- **Lepsza responsywność** — **[+]** **[✓]**
- **PWA (Progressive Web App)** — **[+]** **[✓]** **[🔐]** (instalacja, offline support, service worker)

## 9. Media i zasoby
- **Zdjęcia przedmiotów (galeria obrazów)** — **[+]** **[✓]** **[🔐]** (admin-only, multi-image, drag-and-drop upload, local/S3 storage)

## 10. Funkcje AI
- **Infrastruktura AI (chat, historia, tokeny, modele)** — **[+]** **[✓]** **[🔐]** (zaimplementowane: chat interface, model selection, historia)  
- **Sugestie sprzętu (na podstawie pogody, aktywności itp.)** — **[→]** **[🔐]** (planowane)  
- **Analiza listy (co dodać, co usunąć, alternatywy)** — **[→]** **[🔐]** (planowane)  
- **Automatyczne oznaczanie kategorii / worn / consumable** — **[→]** **[🔐]** (planowane)  
- **Generowanie gotowych presetów (UL, bushcraft, EDC)** — **[→]** **[🔐]** (planowane)  
- **Konwersja: opis → gotowy kontener** — **[→]** **[🔐]** (planowane)

## 11. Ustawienia użytkownika
- **Preferowana jednostka wagi (domyślna)** — **[✓]** **[🔐]** (g, kg, oz, lb) - localStorage + synchronizacja z backendem zaimplementowana  
- **Dodawanie nowych kategorii** — **[+]** **[✓]** **[🔐]** (localStorage + synchronizacja z backendem zaimplementowana)  
- **Dodawanie firm / marek (brand)** — **[+]** **[✓]** **[🔐]** (localStorage + synchronizacja z backendem zaimplementowana)  
- **Domyślna waluta i widoczność nowych kontenerów** — **[✓]** **[🔐]** (localStorage + synchronizacja z backendem zaimplementowana)

---

## 📊 Podsumowanie statusu

### ✅ Zaimplementowane (gotowe)
- Wszystkie podstawowe funkcjonalności struktury danych (hierarchiczne kontenery, przedmioty)
- System wag i jednostek (kg, g, oz, lb) z automatycznym sumowaniem
- Wykresy wagowe i analityka
- Ceny i waluty (z synchronizacją backend)
- Eksport/import Markdown
- Zarządzanie elementami (kopiowanie, katalog, autocomplete, linkowanie)
- Udostępnianie kontenerów (publiczne linki, galeria, ocenianie)
- Przeglądarki kontenerów i przedmiotów
- PWA (Progressive Web App)
- Zdjęcia przedmiotów (galeria, upload, S3)
- Infrastruktura AI (chat, historia, tokeny, modele)
- Ustawienia użytkownika (jednostki, kategorie, marki, waluta, widoczność)

### 🔄 Planowane (do zrobienia)

#### Wysoki priorytet
1. **Komentarze pod kontenerami** — **[🔐]** (wymaga backendu)
2. **Globalny katalog itemów (multi-user)** — **[🔐]** (backend, synchronizacja między użytkownikami)
3. **Przenoszenie przedmiotów między kontenerami** — **[🔐]** (backend)
4. **Statystyki wyświetleń kontenerów** — **[🔐]** (backend, tracking)

#### Średni priorytet
1. **Wizualizacja podziału wag (worn vs base vs consumable)** — (front-end, wykres breakdown)
   - **Feature:** [FEATURE-027](./features/FEATURE-027-weight-breakdown-visualization.md)
   - Wykres kołowy pokazujący podział wag na base/worn/consumable
   - Obliczanie wag per kategoria z obsługą zagnieżdżonych kontenerów
   - Inspiracja: LighterPack pokazuje podział wag
2. **Markdown w notatkach / opisach** — (front-end, renderowanie Markdown)
3. **Funkcje AI:**
   - Sugestie sprzętu (na podstawie pogody, aktywności)
   - Analiza listy (co dodać, co usunąć, alternatywy)
   - Automatyczne oznaczanie kategorii / worn / consumable
   - Generowanie gotowych presetów (UL, bushcraft, EDC)
   - Konwersja: opis → gotowy kontener
4. **Oznaczanie kontenerów jako fragmentów rodzica** — (front-end)
5. **Zwijanie sekcji statystyk** — (front-end, localStorage)
6. **Obsługa różnych formatów importu** (CSV, JSON) — (front-end)

#### Niski priorytet
1. **Warianty kontenera** — (ten sam kontener, różna zawartość)
2. **Porównywarka kontenerów** — **[🔐]** (backend)
3. **Automatyczne wyszukiwanie obrazków dla przedmiotów** — **[🔐]** (backend)
4. **Generowanie SVG z obrazków** — **[🔐]** (backend)
5. **Wersjonowanie danych (historia zmian)** — **[🔐]** (backend)
6. **System zaproszeń** — **[🔐]** (backend)
7. **Szablony kontenerów** — **[🔐]** (backend)

---

## 🎯 Co jest do wdrożenia z tego pliku?

### Funkcje oznaczone jako **[→]** (planowane):

1. **Markdown w notatkach / opisach list i przedmiotów** (sekcja 4)
   - Renderowanie Markdown w notatkach i opisach
   - Front-end only (nie wymaga backendu)
   - Status: 🔄 Planned w ROADMAP_OFFLINE.md

2. **Komentarze pod kontenerami** (sekcja 6)
   - System komentarzy dla publicznych kontenerów
   - Wymaga backendu/DB **[🔐]**
   - Status: 🔄 Planned w ROADMAP_ONLINE.md

3. **Funkcje AI** (sekcja 10) - wszystkie planowane:
   - Sugestie sprzętu (na podstawie pogody, aktywności)
   - Analiza listy (co dodać, co usunąć, alternatywy)
   - Automatyczne oznaczanie kategorii / worn / consumable
   - Generowanie gotowych presetów (UL, bushcraft, EDC)
   - Konwersja: opis → gotowy kontener
   - Wszystkie wymagają backendu **[🔐]**
   - Status: 🔄 Planned w ROADMAP_ONLINE.md
   - **Uwaga:** Infrastruktura AI (chat, historia, tokeny) jest już zaimplementowana ✅

---

## 🔍 Co jest w LighterPack, czego nie ma u nas?

### Porównanie funkcji podstawowych:

| Funkcja | LighterPack | Nasza aplikacja | Status |
|---------|-------------|-----------------|--------|
| **Listy ekwipunku** | ✅ Lists (płaskie) | ✅ Kontenery (hierarchiczne) | ✅ **[+]** Lepsze - mamy hierarchię |
| **Przedmioty z wagą** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Automatyczne sumowanie wag** | ✅ | ✅ | ✅ **[≠]** Lepsze - rekurencyjne |
| **Wykresy wagowe** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Jednostki wagi (kg/g)** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Jednostki imperialne (lb/oz)** | ✅ | ✅ | ✅ Zaimplementowane |
| **Ceny produktów** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Notatki tekstowe** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Markdown w notatkach** | ❓ Nie wiadomo | 🔄 Planowane | 🔄 Do wdrożenia |
| **Kopiowanie/klonowanie list** | ✅ | ✅ | ✅ Zaimplementowane |
| **Publiczne udostępnianie** | ✅ | ✅ | ✅ **[=]** Pokrywa się |
| **Galeria publiczna** | ❌ | ✅ | ✅ **[+]** Mamy więcej |
| **Ocenianie (gwiazdki)** | ❌ | ✅ | ✅ **[+]** Mamy więcej |
| **Komentarze** | ❓ Nie wiadomo | 🔄 Planowane | 🔄 Do wdrożenia |
| **Zdjęcia przedmiotów** | ❌ | ✅ | ✅ **[+]** Mamy więcej |
| **PWA (offline)** | ❌ | ✅ | ✅ **[+]** Mamy więcej |
| **Funkcje AI** | ❌ | 🔄 Planowane | 🔄 Do wdrożenia |

### Funkcje LighterPack, które mogą być lepsze:

1. **Interaktywne drag & drop** - LighterPack ma bardzo płynne przeciąganie przedmiotów
   - **U nas:** Mamy drag & drop dla kolejności przedmiotów ✅
   - **Status:** Zaimplementowane, ale może wymagać ulepszeń UX

2. **Szybka edycja inline** - LighterPack pozwala edytować wszystko bezpośrednio w tabeli
   - **U nas:** Mamy w pełni zaimplementowane ✅
   - **Status:** ✅ Completed - inline editing dla: nazwa, ilość, waga, priorytet, status, cena, kategoria, notatki
   - **Feature:** [FEATURE-007](./features/FEATURE-007-inline-editing.md)

3. **Wizualizacja podziału wag (worn vs base vs consumable)** - LighterPack pokazuje podział wag
   - **U nas:** Mamy typy worn/consumable ✅, brak wizualizacji breakdown
   - **Status:** 🔄 Planned - wizualizacja podziału wag w przygotowaniu
   - **Feature:** [FEATURE-027](./features/FEATURE-027-weight-breakdown-visualization.md)

### Funkcje, które mamy lepsze niż LighterPack:

1. ✅ **Hierarchiczne kontenery** - LighterPack ma tylko płaskie listy
2. ✅ **Galeria publiczna** - LighterPack nie ma
3. ✅ **Ocenianie kontenerów** - LighterPack nie ma
4. ✅ **Zdjęcia przedmiotów** - LighterPack nie ma
5. ✅ **PWA (offline support)** - LighterPack nie ma
6. ✅ **Eksport/import Markdown** - LighterPack nie ma
7. ✅ **Linkowanie przedmiotów** - LighterPack nie ma
8. ✅ **Poziomy widoczności** - LighterPack ma tylko publiczne/prywatne

---

## 📝 Uwagi
- Większość podstawowych funkcjonalności jest już zaimplementowana
- **Główne różnice:** Mamy więcej funkcji niż LighterPack (hierarchia, galeria, ocenianie, PWA, AI)
- **Główne luki:** Markdown w notatkach, komentarze, wizualizacja podziału wag, zaawansowane funkcje AI
- Większość planowanych funkcji wymaga backendu/DB/auth (oznaczone **[🔐]**)
- Szczegółowe plany implementacji znajdują się w [ROADMAP.md](./ROADMAP.md), [ROADMAP_OFFLINE.md](./ROADMAP_OFFLINE.md) i [ROADMAP_ONLINE.md](./ROADMAP_ONLINE.md)
