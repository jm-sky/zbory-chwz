# Design & UX Review — Zbory CHWZ

**Status:** `done`  
**Created:** 2026-07-21  
**Viewporty:** Desktop 1440×900, Mobile 375×812  
**Motyw:** Light only  
**Konto testowe:** test@zbory.chwz.waw.pl (Owner)  
**Środowisko:** `pnpm dev` (localhost:5176) + Docker backend (localhost:8002)

---

## Podsumowanie wykonawcze

Przegląd obejmował 50 screenshotów (25 desktop + 25 mobile) głównych ekranów aplikacji: lista zborów, szczegóły, auth, strony publiczne, profil, ustawienia, grupy, katalog osób, edycja zboru oraz panel admin.

Aplikacja ma **spójny, nowoczesny wygląd** (shadcn-vue, karty, gradient tła, czytelna typografia). Największe problemy UX to **niedziałający widok mapy** (brak współrzędnych + niedostępna mapa), **mieszanka języków PL/EN**, **pozostałości copy z szablonu Gear Stack** w ustawieniach oraz **bardzo długi formularz edycji zboru** na mobile.

| Kategoria | Ocena | Uwagi |
|-----------|-------|-------|
| **Layout** | ⭐⭐⭐⭐☆ | Czytelna hierarchia, spójny header/footer, dobre karty na liście zborów |
| **UX** | ⭐⭐⭐☆☆ | Mapa bezużyteczna, długa edycja, brak linku rejestracji, `confirm()` zamiast dialogów |
| **RWD** | ⭐⭐⭐⭐☆ | Lista i szczegóły dobrze się skalują; edycja zboru wymaga dużo scrollowania |
| **Accessibility** | ⭐⭐⭐☆☆ | Menu użytkownika ma aria-label; niski kontrast linków na loginie i stopce |
| **Spójność** | ⭐⭐⭐☆☆ | Mieszanka PL/EN, legacy copy „containers/items”, różne lata w copyright |

---

## Metodologia

1. Uruchomienie środowiska: `docker compose up -d`, `pnpm dev`
2. Automatyczne screenshoty: Playwright (`scripts/playwright/capture-ux-review.ts`)
3. Weryfikacja interakcji: przełącznik widoków (siatka/lista/mapa), menu użytkownika, logowanie kontem testowym
4. Ocena: layout, UX flow, RWD (desktop vs mobile), a11y, spójność i18n

**Ograniczenia tego przebiegu:** tylko light mode; brak testu screen readera; mapa Google wymaga klucza API — stan „niedostępna” udokumentowany jako finding UX, nie jako bug infrastruktury.

---

## Przegląd per ekran

### 1. Lista zborów (`/`) — gość

![Desktop — lista zborów](assets/2026-07-21--design-ux/desktop/desktop--landing--guest.png)  
![Mobile — lista zborów](assets/2026-07-21--design-ux/mobile/mobile--landing--guest.png)

**Route:** `/` · **Rola:** gość

✅ **Mocne strony**
- Czytelne karty z ikoną, adresem, godzinami, pastorem, telefonem i e-mailem
- Wyszukiwarka + przycisk „Więcej” (filtry) + przełącznik Siatka / Lista / Mapa
- Licznik wyników (29–30 zborów po seedzie)
- Na mobile karty przechodzą w jedną kolumnę bez łamania layoutu

⚠️ **Uwagi**
- Wszystkie zseedowane zbiory mają badge „Niezweryfikowany” — dla użytkownika publicznego może sugerować błąd danych zamiast statusu redakcyjnego
- Domyślny język interfejsu to EN (nagłówek „CHWZ Congregations”), choć treść zborów jest po polsku
- Brak widocznej paginacji przy ~30 pozycjach (akceptowalne na razie, problem przy skali)

🔴 **Problemy**
- Widok mapy pokazuje „Mapa jest chwilowo niedostępna” + „30 zborów bez współrzędnych nie jest pokazanych” — funkcja mapy jest de facto wyłączona po seedzie

**RWD:** Mobile zachowuje pełną funkcjonalność toolbaru; karty są czytelne, ale długa lista wymaga scrollowania bez skrótów (np. sticky search).

---

### 2. Lista zborów — widok mapy (`/`)

![Desktop — mapa](assets/2026-07-21--design-ux/desktop/desktop--landing-map--guest.png)  
![Mobile — mapa](assets/2026-07-21--design-ux/mobile/mobile--landing-map--guest.png)

**Route:** `/` (widok Mapa)

⚠️ Pusty placeholder z komunikatem — brak alternatywy (np. lista zborów bez geo, CTA „Dodaj współrzędne” dla edytorów).

---

### 3. Szczegóły zboru (`/congregations/:id`) — gość

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--congregation-detail--guest.png)  
![Mobile](assets/2026-07-21--design-ux/mobile/mobile--congregation-detail--guest.png)

**Przykład:** Zbór Warszawa I (`01KY1SPKX9317P0E6EJN4F6MJ8`)

✅ Przycisk „Wstecz”, sekcje Adres / Godziny / Kontakt z ikonami  
⚠️ Opis zawiera surowy tekst `Website: chwz.waw.pl` zamiast klikalnego linku  
⚠️ Brak mapy, zdjęcia, przycisków „Zadzwoń” / „Nawiguj” na mobile  
✅ Mobile: sekcje czytelne, footer w kolumnie

---

### 4. Logowanie (`/auth/login`) — gość

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--auth-login--guest.png)  
![Mobile](assets/2026-07-21--design-ux/mobile/mobile--auth-login--guest.png)

✅ Minimalistyczny layout, toggle hasła, link „Zapomniałeś hasła?”  
⚠️ Brak linku do rejestracji (zgodne z `REGISTRATION_ENABLED=false`, ale brak komunikatu „kontakt z administratorem”)  
⚠️ Niski kontrast szarego tekstu stopki i linku reset hasła

---

### 5. Rejestracja (`/auth/register`) — gość

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--auth-register--guest.png)  
![Mobile](assets/2026-07-21--design-ux/mobile/mobile--auth-register--guest.png)

Formularz dostępny pod URL, mimo wyłączonej rejestracji w backendzie — potencjalne rozczarowanie użytkownika.

---

### 6. Strony publiczne (`/about`, `/privacy`, `/cookies`, `/terms`, `/contact`)

Spójny layout `MainLayout` — treść w białej karcie, header i footer jak na liście.  
✅ Czytelne na desktop i mobile  
⚠️ Treść prawna w EN przy polskiej nazwie aplikacji (jeśli locale=EN)

---

### 7. Strona 404

![Desktop 404](assets/2026-07-21--design-ux/desktop/desktop--not-found--guest.png)

✅ Czytelny komunikat po polsku, CTA „Przejdź do Zborów”  
⚠️ Mieszane etykiety: nagłówek PL, przyciski „Dashboard” / „Settings” bez tłumaczenia  
⚠️ Brak layoutu aplikacji (goły ekran) — celowe, ale brak spójnego headera

---

### 8. Lista zborów — zalogowany Owner

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--landing--logged-in.png)

✅ Przycisk „+” do tworzenia zboru widoczny dla Owner  
✅ Menu użytkownika rozbudowane (patrz niżej)

---

### 9. Menu użytkownika

![Desktop — dropdown](assets/2026-07-21--design-ux/desktop/desktop--user-menu--logged-in.png)

✅ Avatar z inicjałami, e-mail, logout osobno  
⚠️ 6 pozycji w menu (Profile, Settings, People groups, Email export, People browser, Admin) — dużo na mobile; rozważyć grupowanie lub sidebar dla admina

---

### 10. Profil (`/profile`, `/profile/edit`)

![Desktop profil](assets/2026-07-21--design-ux/desktop/desktop--profile--logged-in.png)  
![Mobile profil](assets/2026-07-21--design-ux/mobile/mobile--profile--logged-in.png)

✅ Standardowy układ profilu z przyciskiem edycji  
✅ Formularz edycji czytelny na obu viewportach

---

### 11. Ustawienia (`/settings`)

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--settings--logged-in.png)

✅ Sekcje: Preferences, Security (2FA, passkeys), OAuth, Storage, Delete Account  
🔴 **Copy z szablonu Gear Stack:** „You will lose access to all your containers and items” w sekcji Delete Account  
⚠️ Storage Usage pokazuje skeleton/loadery bez danych  
⚠️ „Image Processing Mode” — funkcja nieadekwatna do domeny zborów (pozostałość szablonu)

---

### 12. Grupy (`/groups`)

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--groups-list--logged-in.png)  
![Mobile](assets/2026-07-21--design-ux/mobile/mobile--groups-list--logged-in.png)

✅ Empty state „No groups” + CTA „New group”  
✅ Krótki opis modułu

---

### 13. Katalog osób (`/people-directory`, `/people-directory/persons`)

![Eksport](assets/2026-07-21--design-ux/desktop/desktop--directory-export--logged-in.png)  
![Przeglądarka](assets/2026-07-21--design-ux/desktop/desktop--directory-persons--logged-in.png)

✅ Przeglądarka osób z wyszukiwarką i edycją inline  
✅ Role i zbor przypisane do każdej osoby  
⚠️ Długa lista bez paginacji — przy setkach rekordów będzie problem

---

### 14. Edycja zboru (`/congregations/:id/edit`)

![Desktop](assets/2026-07-21--design-ux/desktop/desktop--congregation-edit--logged-in.png)  
![Mobile](assets/2026-07-21--design-ux/mobile/mobile--congregation-edit--logged-in.png)

✅ Pasek „Profile completeness” (83%) z listą brakujących pól — bardzo pomocne UX  
✅ Sekcje: Basic info, Address, Service times, People, Branches, Share link, History  
✅ Autouzupełnianie osób (`PersonSuggestionsList`) — poprawa względem wcześniejszego review  
⚠️ Osobny przycisk „Save” w każdej sekcji — użytkownik może nie wiedzieć, która sekcja wymaga zapisu  
⚠️ Mapa w sekcji Address: „Map is temporarily unavailable”  
⚠️ Mobile: ekstremalnie długi scroll (7 sekcji) — brak sticky nav / anchor menu  
⚠️ Usuwanie osoby używa `window.confirm()` zamiast spójnego `Dialog` (plik: `ChurchPeopleSection.vue`)

---

### 15. Panel admin

| Ekran | Screenshot desktop |
|-------|-------------------|
| Dashboard | `desktop--admin-dashboard--logged-in.png` |
| Users | `desktop--admin-users--logged-in.png` |
| Congregations | `desktop--admin-congregations--logged-in.png` |
| Import | `desktop--admin-import--logged-in.png` |
| Share links | `desktop--admin-share-links--logged-in.png` |

✅ Spójny layout z resztą aplikacji, tabele z paginacją i filtrem kolumn  
⚠️ Tabela użytkowników: większość kont „Unverified” (czerwony badge) — wizualnie alarmujące mimo że to konto techniczne z seeda  
✅ Mobile: tabele admin działają (screenshoty w `mobile/`)

Konto testowe ma rolę **Owner** — pełny dostęp do panelu admin potwierdzony.

---

## Findings

| ID | Severity | Obszar | Opis | Plik / ekran |
|----|----------|--------|------|--------------|
| UX-1 | **high** | Mapa | Widok mapy bezużyteczny: brak współrzędnych w seedzie + komunikat „Mapa jest chwilowo niedostępna”. Użytkownik nie widzi żadnych markerów. | `CongregationsMapView`, seeder |
| UX-2 | **medium** | i18n | Domyślny locale EN (`VITE_DEFAULT_LOCALE=en`) przy polskiej domenie i treści zborów. Mieszanka PL/EN w jednym ekranie. | `.env`, `src/shared/i18n/` |
| UX-3 | **medium** | Copy | Ustawienia zawierają teksty z szablonu Gear Stack („containers and items”, image processing). | `src/modules/settings/i18n/locales/en.ts` |
| UX-4 | **medium** | Edycja zboru | Formularz edycji bardzo długi na mobile; brak nawigacji między sekcjami (tabs/anchors). | `EditCongregationPage.vue` |
| UX-5 | **medium** | Zapis | Wiele przycisków „Save” per sekcja — ryzyko utraty zmian lub niejasności zakresu zapisu. | `EditCongregationPage.vue` |
| UX-6 | **medium** | Potwierdzenia | Usuwanie osoby ze służby przez natywny `confirm()` zamiast komponentu Dialog. | `ChurchPeopleSection.vue:294` |
| UX-7 | **medium** | Szczegóły zboru | Website w opisie jako plain text, brak linków `tel:` / `mailto:` / nawigacji. | `CongregationDetailPage.vue` |
| UX-8 | **low** | Statusy | Badge „Niezweryfikowany” na wszystkich zseedowanych zborach — mylące dla gościa. | `CongregationListCard.vue` |
| UX-9 | **low** | Auth | Brak informacji przy wyłączonej rejestracji (formularz `/auth/register` nadal dostępny). | `RegisterPage.vue`, backend |
| UX-10 | **low** | 404 | Mieszane języki w przyciskach nawigacji (PL + EN). | `NotFoundPage.vue` |
| UX-11 | **low** | Footer | Niespójny rok copyright (2024 vs 2026) między ekranami. | `AppFooter.vue` |
| UX-12 | **low** | A11y | Niski kontrast szarych linków na stronie logowania i w stopce mobile. | `LoginPage.vue`, `AppFooter.vue` |
| UX-13 | **low** | Admin | Badge „Unverified” dominuje w tabeli użytkowników po seedzie — rozważyć auto-verify dla kont technicznych lub stonować kolor. | `AdminUsersPage.vue` |

**Pozytywne obserwacje (bez severity):**
- Pasek kompletności profilu zboru — dobra praktyka UX
- Autouzupełnianie osób w sekcji „Ludzie i służby” — wdrożone (`usePersonAutocomplete`)
- Spójny design system (karty, przyciski, ikony lucide)
- Lista zborów: trzy tryby widoku, filtry, eksport (menu w toolbarze)

---

## Rekomendacje

### Priorytet 1 (wysoki)

1. **Naprawić widok mapy end-to-end** — geokodowanie przy seedzie lub batch geocode + skonfigurowany klucz Google Maps; gdy brak mapy, ukryć zakładkę „Mapa” lub pokazać listę zborów z adresem zamiast pustego prostokąta.
2. **Ustawić domyślny locale na `pl`** i przejrzeć klucze EN pod kątem domeny CHWZ.
3. **Usunąć / przetłumaczyć legacy copy** w ustawieniach (containers, items, image processing).

### Priorytet 2 (średni)

4. **Edycja zboru:** dodać sticky sub-nav (kotwice do sekcji) lub tabs; rozważyć jeden globalny „Zapisz wszystko” z autosave per sekcja.
5. **Zamienić `confirm()` na `Dialog`** przy usuwaniu osób i innych akcjach destrukcyjnych.
6. **Szczegóły zboru:** klikalny website, `tel:` / `mailto:`, opcjonalnie mini-mapa lub link do Google Maps.
7. **Menu użytkownika:** pogrupować linki admina / katalogu lub przenieść do sidebaru na desktop.

### Priorytet 3 (niski)

8. Wyjaśnić badge „Niezweryfikowany” tooltipem lub zmienić copy na „Do weryfikacji przez admina”.
9. Ujednolicić copyright i tłumaczenia na stronie 404.
10. Paginacja lub virtual scroll w przeglądarce osób i liście zborów (>50 pozycji).

---

## Załączniki — indeks screenshotów

### Desktop (`assets/2026-07-21--design-ux/desktop/`)

| Plik | Ekran |
|------|-------|
| `desktop--landing--guest.png` | Lista zborów (gość) |
| `desktop--landing-map--guest.png` | Widok mapy (gość) |
| `desktop--auth-login--guest.png` | Logowanie |
| `desktop--auth-register--guest.png` | Rejestracja |
| `desktop--congregation-detail--guest.png` | Szczegóły zboru |
| `desktop--about--guest.png` | O aplikacji |
| `desktop--privacy--guest.png` | Polityka prywatności |
| `desktop--cookies--guest.png` | Ciasteczka |
| `desktop--terms--guest.png` | Regulamin |
| `desktop--contact--guest.png` | Kontakt |
| `desktop--not-found--guest.png` | 404 |
| `desktop--landing--logged-in.png` | Lista (Owner) |
| `desktop--profile--logged-in.png` | Profil |
| `desktop--profile-edit--logged-in.png` | Edycja profilu |
| `desktop--settings--logged-in.png` | Ustawienia |
| `desktop--groups-list--logged-in.png` | Grupy |
| `desktop--directory-export--logged-in.png` | Eksport e-mail |
| `desktop--directory-persons--logged-in.png` | Przeglądarka osób |
| `desktop--congregation-edit--logged-in.png` | Edycja zboru |
| `desktop--admin-dashboard--logged-in.png` | Admin dashboard |
| `desktop--admin-users--logged-in.png` | Admin użytkownicy |
| `desktop--admin-congregations--logged-in.png` | Admin zbiory |
| `desktop--admin-import--logged-in.png` | Import zborów |
| `desktop--admin-share-links--logged-in.png` | Linki udostępniania |
| `desktop--user-menu--logged-in.png` | Menu użytkownika |

### Mobile (`assets/2026-07-21--design-ux/mobile/`)

Analogiczny zestaw 25 plików (`mobile--*.png`), w tym `mobile--landing-map--guest.png`.

**Skrypt regeneracji:** `npx tsx scripts/playwright/capture-ux-review.ts`

---

## Powiązane dokumenty

- [2026-07-10--church-platform-review.md](2026-07-10--church-platform-review.md) — security i zgodność z planem (nie duplikowane tutaj)
- [2025-01-20--ux-review.md](2025-01-20--ux-review.md) — wcześniejszy review (szablon Gear Stack)
