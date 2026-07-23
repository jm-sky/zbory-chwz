# Plan: model zborów, uprawnienia i URL

## Hierarchia uprawnień edycji zborów

System powinien obsługiwać hierarchię:

```
Admin
├── Biskup
│   └── wszystkie zbory wspólnoty
├── Biskup rejonu
│   └── zbory przypisane do rejonu
└── Pastor
    └── własny zbór
```

Do przygotowania wizualizacja hierarchii w Canvas.

Należy ustalić:
- kto może tworzyć zbory,
- kto może zmieniać pastora,
- kto może przenosić zbór między rejonami,
- zakres widoczności danych.

## URL i routing

### Kanoniczny URL zboru

Adres konkretnego zboru powinien mieć pełną hierarchię:

```
/kraj/miasto/slug-zboru
```

Przykład:

```
/polska/warszawa/przyce
```

Ostatni segment powinien być stabilnym slugiem zboru, a nie bezpośrednio nazwą ulicy, aby zmiana lokalizacji nie wymuszała zmiany URL.

### Dynamiczne adresy

Adresy agregujące:

```
/polska
/polska/warszawa
/warszawa
```

`/warszawa` może działać jako skrócony alias.

Logika:
- jeden wynik → przejście do strony zboru,
- wiele wyników → lista/karty wyboru,
- brak wyniku → strona błędu lub sugestie.

Przykład:
Warszawa może mieć wiele zborów tej samej lub różnych wspólnot, więc miasto jest tylko filtrem, nie jednoznacznym identyfikatorem.

## Wspólnoty

Obsługa wielu wspólnot przez osobny model:

```
communities
- id
- name
- slug
- visibility
```

Zbory posiadają:

```
churches
- community_id (FK)
```

Nowe wspólnoty domyślnie ukryte.

## Widoczność danych

Jeden wspólny mechanizm widoczności dla:
- zborów,
- służb,
- osób,
- dokumentów,
- wydarzeń.

Poziomy:

```
hidden
public
authenticated
pastors
```

Przykłady:
- dane publiczne zboru → public,
- wewnętrzne informacje → authenticated,
- osoby odpowiedzialne za szczególne służby → pastors,
- robocze wpisy → hidden.

Widoczność i uprawnienia edycji powinny być rozdzielone.