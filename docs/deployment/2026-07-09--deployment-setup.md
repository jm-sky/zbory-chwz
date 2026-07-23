# Konfiguracja deploymentu

## Struktura użytkowników

- **Użytkownik deploy**: Używany przez GitHub Actions do automatycznego deploymentu
- **Inni użytkownicy**: Dodani do grupy `deploy` dla dostępu do projektu

## Krok 1: Konfiguracja katalogu projektu

Projekt powinien być przechowywany w katalogu użytkownika (np. `~/apps/gear-stack`).

```bash
# Utwórz katalog aplikacji
sudo mkdir -p ~/apps/gear-stack
sudo chown deploy:deploy ~/apps/gear-stack
sudo chmod 2775 ~/apps/gear-stack  # setgid - nowe pliki dziedziczą grupę

# Sklonuj projekt
sudo -u deploy git clone <repo-url> ~/apps/gear-stack
```

## Krok 2: Dodaj innych użytkowników do grupy deploy

Jeśli chcesz, aby inni użytkownicy mieli dostęp do projektu:

```bash
# Dodaj użytkownika do grupy deploy
sudo usermod -aG deploy <username>

# Ustaw uprawnienia dla istniejących plików
sudo chown -R deploy:deploy ~/apps/gear-stack
sudo chmod -R g+w ~/apps/gear-stack
sudo find ~/apps/gear-stack -type d -exec chmod g+s {} \;
```

**Ważne**: Po dodaniu do grupy, użytkownik musi się wylogować i zalogować ponownie.

## Krok 3: Konfiguracja uprawnień do /var/www/gear-stack

### Opcja A: Grupa Caddy (zalecane)

```bash
# Dodaj użytkownika deploy do grupy caddy
sudo usermod -aG caddy deploy

# Ustaw właściciela i grupę
sudo chown -R caddy:caddy /var/www/gear-stack

# Ustaw uprawnienia: właściciel i grupa mogą zapisywać, inni tylko czytać
sudo chmod -R 775 /var/www/gear-stack

# Ustaw setgid bit, aby nowe pliki dziedziczyły grupę
sudo chmod g+s /var/www/gear-stack
```

### Opcja B: Sudo bez hasła (alternatywa)

Jeśli powyższe nie działa, skonfiguruj sudoers:

```bash
sudo visudo
```

Dodaj linię:
```
deploy ALL=(ALL) NOPASSWD: /usr/bin/rsync, /usr/bin/mkdir
```

## Krok 4: Uprawnienia Docker (jeśli backend używa Docker)

```bash
# Dodaj użytkownika deploy do grupy docker
sudo usermod -aG docker deploy
```

## Weryfikacja

### Sprawdź uprawnienia do projektu:

```bash
# Jako użytkownik deploy lub użytkownik w grupie deploy
cd ~/apps/gear-stack
ls -la  # Powinno działać bez błędów
```

### Sprawdź uprawnienia do /var/www/gear-stack:

```bash
# Jako użytkownik deploy
touch /var/www/gear-stack/test.txt
rm /var/www/gear-stack/test.txt
```

Jeśli działa bez sudo, konfiguracja jest poprawna.

### Sprawdź członkostwo w grupach:

```bash
# Sprawdź grupy użytkownika
groups deploy
# Powinno pokazać: deploy caddy docker (lub podobne)

# Dla innych użytkowników
groups <username>
# Powinno pokazać grupę deploy
```

## Uwagi

- Po zmianie grup, użytkownicy muszą się wylogować i zalogować ponownie
- Skrypt `deploy.sh` automatycznie wykrywa, czy może zapisywać bez sudo
- GitHub Actions używa domyślnie `~/apps/gear-stack` (czyli `~/apps/gear-stack`)

