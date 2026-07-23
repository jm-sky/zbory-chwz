# Database Migration Guide

Przewodnik migracji danych PostgreSQL między serwerami VPS.

## Wymagania

- Dostęp SSH do obu serwerów
- Docker zainstalowany na obu serwerach
- Kontener PostgreSQL uruchomiony na obu serwerach

## Metoda 1: Automatyczna migracja (zalecana)

### Użycie skryptu interaktywnego

```bash
cd backend/scripts
./migrate-db.sh user@stary-serwer.com user@nowy-serwer.com
```

Skrypt:
1. Tworzy dump bazy na starym serwerze
2. Kopiuje dump na nowy serwer
3. Restoruje bazę na nowym serwerze
4. Czyści pliki tymczasowe

### Użycie skryptu nieinteraktywnego

```bash
cd backend/scripts
OLD_SERVER=user@stary-serwer.com NEW_SERVER=user@nowy-serwer.com ./migrate-db-simple.sh
```

**Uwaga:** Skrypt nieinteraktywny nie pyta o potwierdzenie i nadpisze istniejące dane!

## Metoda 2: Ręczna migracja

### Krok 1: Utwórz dump na starym serwerze

```bash
# Połącz się ze starym serwerem
ssh user@stary-serwer.com

# Utwórz dump
docker exec gear-stack-db pg_dump -U backend -d backend --clean --if-exists --no-owner --no-acl > /tmp/db-dump.sql

# Sprawdź rozmiar
ls -lh /tmp/db-dump.sql
```

### Krok 2: Skopiuj dump na nowy serwer

```bash
# Z lokalnego komputera
scp user@stary-serwer.com:/tmp/db-dump.sql user@nowy-serwer.com:/tmp/db-dump.sql
```

### Krok 3: Zrestoruj na nowym serwerze

```bash
# Połącz się z nowym serwerem
ssh user@nowy-serwer.com

# Zrestoruj bazę (UWAGA: nadpisze istniejące dane!)
docker exec -i gear-stack-db psql -U backend -d backend < /tmp/db-dump.sql

# Sprawdź czy dane są na miejscu
docker exec gear-stack-db psql -U backend -d backend -c "\dt"
```

### Krok 4: Wyczyść pliki tymczasowe

```bash
# Na starym serwerze
rm /tmp/db-dump.sql

# Na nowym serwerze
rm /tmp/db-dump.sql
```

## Metoda 3: Bezpośrednia migracja (bez pliku pośredniego)

Jeśli masz szybkie połączenie między serwerami:

```bash
# Z lokalnego komputera
ssh user@stary-serwer.com "docker exec gear-stack-db pg_dump -U backend -d backend --clean --if-exists --no-owner --no-acl" | \
  ssh user@nowy-serwer.com "docker exec -i gear-stack-db psql -U backend -d backend"
```

## Weryfikacja migracji

Po migracji sprawdź:

```bash
# Połącz się z nowym serwerem
ssh user@nowy-serwer.com

# Sprawdź tabele
docker exec gear-stack-db psql -U backend -d backend -c "\dt"

# Sprawdź liczbę rekordów w głównych tabelach
docker exec gear-stack-db psql -U backend -d backend -c "SELECT COUNT(*) FROM users;"
docker exec gear-stack-db psql -U backend -d backend -c "SELECT COUNT(*) FROM gear_containers;"
```

## Rozwiązywanie problemów

### Problem: "container not found"

Upewnij się, że kontener ma poprawną nazwę:
```bash
docker ps | grep postgres
```

Jeśli nazwa jest inna, ustaw zmienną:
```bash
export DB_CONTAINER="twoja-nazwa-kontenera"
```

### Problem: "permission denied"

Upewnij się, że masz uprawnienia do:
- SSH na obu serwerach
- Docker na obu serwerach (może wymagać `sudo` lub dodania użytkownika do grupy `docker`)

### Problem: "database does not exist"

Upewnij się, że baza istnieje na nowym serwerze:
```bash
docker exec gear-stack-db psql -U backend -l
```

Jeśli nie istnieje, utwórz ją:
```bash
docker exec gear-stack-db psql -U backend -c "CREATE DATABASE backend;"
```

### Problem: "connection refused"

Upewnij się, że kontener PostgreSQL jest uruchomiony:
```bash
docker ps | grep gear-stack-db
```

Jeśli nie działa, uruchom:
```bash
cd backend
docker-compose -f docker-compose.dev.yml up -d db
```

## Migracja plików (uploads)

Jeśli masz pliki w `/app/uploads`, skopiuj je również:

```bash
# Z lokalnego komputera
scp -r user@stary-serwer.com:/path/to/uploads/* user@nowy-serwer.com:/path/to/uploads/
```

Lub użyj rsync (lepsze dla dużych plików):
```bash
rsync -avz --progress user@stary-serwer.com:/path/to/uploads/ user@nowy-serwer.com:/path/to/uploads/
```

## Bezpieczeństwo

- Zawsze rób backup przed migracją
- Używaj szyfrowanego połączenia SSH
- Usuń pliki dump po migracji
- Sprawdź czy dane zostały poprawnie zmigrowane przed usunięciem starego serwera

