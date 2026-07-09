# Rozwiązywanie problemów z SSH w GitHub Actions

## Błąd: "unable to authenticate, attempted methods [none publickey]"

Ten błąd oznacza, że klucz SSH nie może być użyty do autentykacji. Sprawdź poniższe kroki:

## Krok 1: Sprawdź format klucza SSH w GitHub Secrets

Klucz prywatny w `VPS_SSH_KEY` musi:
- Zawierać **całą** zawartość pliku klucza
- Zaczynać się od `-----BEGIN` i kończyć na `-----END`
- Mieć **znak nowej linii na końcu** (ważne!)

### Jak sprawdzić:

1. Wygeneruj klucz (jeśli jeszcze nie masz):
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_deploy
```

2. Wyświetl klucz prywatny:
```bash
cat ~/.ssh/github_actions_deploy
```

3. **Kopiuj CAŁĄ zawartość**, włącznie z:
   - `-----BEGIN OPENSSH PRIVATE KEY-----`
   - całą zawartością środkową
   - `-----END OPENSSH PRIVATE KEY-----`
   - **znakiem nowej linii na końcu**

4. Wklej do GitHub Secret `VPS_SSH_KEY`

## Krok 2: Dodaj publiczny klucz do VPS

Na VPS wykonaj:

```bash
# 1. Sprawdź czy katalog .ssh istnieje
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. Dodaj publiczny klucz (z lokalnego komputera)
# Skopiuj zawartość z: cat ~/.ssh/github_actions_deploy.pub
echo "TUTAJ_WKLEJ_PUBLICZNY_KLUCZ" >> ~/.ssh/authorized_keys

# 3. Ustaw poprawne uprawnienia
chmod 600 ~/.ssh/authorized_keys

# 4. Sprawdź właściciela
chown -R $USER:$USER ~/.ssh
```

## Krok 3: Sprawdź konfigurację SSH na VPS

Sprawdź `/etc/ssh/sshd_config`:

```bash
sudo nano /etc/ssh/sshd_config
```

Upewnij się, że są ustawione:
```
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no  # opcjonalnie, dla bezpieczeństwa
```

Po zmianach zrestartuj SSH:
```bash
sudo systemctl restart sshd
```

## Krok 4: Test połączenia lokalnie

Przetestuj połączenie z lokalnego komputera:

```bash
ssh -i ~/.ssh/github_actions_deploy -v użytkownik@vps-host
```

Flaga `-v` pokaże szczegóły autentykacji. Jeśli działa lokalnie, powinno działać też w GitHub Actions.

## Krok 5: Sprawdź GitHub Secrets

Upewnij się, że wszystkie secrets są ustawione:
- `VPS_HOST` - IP lub hostname (bez `ssh://` i portu)
- `VPS_USER` - dokładna nazwa użytkownika
- `VPS_SSH_KEY` - **cały** prywatny klucz z nową linią na końcu
- `VPS_PORT` - port SSH (jeśli inny niż 22)

## Krok 6: Debug w GitHub Actions

Możesz dodać krok debug do workflow (tymczasowo):

```yaml
- name: Test SSH connection
  uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.VPS_SSH_KEY }}
    port: ${{ secrets.VPS_PORT || 22 }}
    script: |
      echo "SSH connection successful!"
      whoami
      pwd
```

## Najczęstsze błędy:

1. **Brak znaku nowej linii na końcu klucza** - GitHub Secrets czasem go usuwa
2. **Nieprawidłowe uprawnienia na VPS** - `.ssh` musi być 700, `authorized_keys` 600
3. **Zły właściciel plików** - `.ssh` i `authorized_keys` muszą należeć do użytkownika
4. **Klucz nie dodany do authorized_keys** - tylko publiczny klucz, nie prywatny!
5. **Błędna nazwa użytkownika** - sprawdź dokładnie `VPS_USER`

## Szybka weryfikacja na VPS:

```bash
# Sprawdź uprawnienia
ls -la ~/.ssh/
# Powinno pokazać:
# drwx------ .ssh
# -rw------- authorized_keys

# Sprawdź zawartość authorized_keys
cat ~/.ssh/authorized_keys
# Powinien zawierać publiczny klucz (zaczyna się od ssh-ed25519 lub ssh-rsa)
```

