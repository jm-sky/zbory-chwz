# Redis Security Features - Testing Guide

## ✅ Status

Redis jest poprawnie skonfigurowany i działa we wszystkich środowiskach docker-compose.

## 🔧 Konfiguracja

### Zmienne środowiskowe (.env)

```bash
# Redis URL - dla Docker użyj redis://redis:6379/0
REDIS_URL="redis://redis:6379/0"

# WebAuthn Configuration
WEBAUTHN_RP_ID="localhost"
WEBAUTHN_RP_NAME="Gear-Stack"
WEBAUTHN_ORIGIN="http://localhost:5176"
```

### Docker Compose

Redis jest dostępny we wszystkich konfiguracjach:
- `docker-compose.yml` - produkcja
- `docker-compose.dev.yml` - development
- `docker-compose.dev-minio.yml` - development z MinIO

## 🧪 Testowanie

### 1. Sprawdź, czy Redis działa

```bash
# Test połączenia
docker exec gear-stack-redis redis-cli ping
# Oczekiwany wynik: PONG

# Sprawdź klucze w Redis
docker exec gear-stack-redis redis-cli KEYS "*"
```

### 2. Test Token Blacklist

#### Krok 1: Zaloguj się i uzyskaj token

```bash
# POST /api/auth/login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Zapisz otrzymany access_token
```

#### Krok 2: Sprawdź, czy token działa

```bash
# GET /api/auth/me
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Powinieneś otrzymać dane użytkownika
```

#### Krok 3: Wyloguj się (blacklist token)

```bash
# POST /api/auth/logout
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Oczekiwany wynik: {"message":"Logged out successfully"}
```

#### Krok 4: Sprawdź Redis

```bash
# Sprawdź, czy token jest w blacklist
docker exec gear-stack-redis redis-cli KEYS "blacklist:token:*"

# Powinien pokazać klucz z hash'em tokenu
```

#### Krok 5: Próba użycia tokenu po wylogowaniu

```bash
# GET /api/auth/me (ponownie z tym samym tokenem)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Oczekiwany wynik: {"detail":"Token has been revoked"}
# Status: 401 Unauthorized
```

### 3. Test WebAuthn Challenge Storage

#### Krok 1: Rozpocznij rejestrację passkey

```bash
# POST /api/two-factor/webauthn/register/initiate
curl -X POST http://localhost:8000/api/two-factor/webauthn/register/initiate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Security Key"
  }'

# Otrzymasz challenge i challengeToken
```

#### Krok 2: Sprawdź Redis

```bash
# Sprawdź, czy challenge jest w Redis
docker exec gear-stack-redis redis-cli KEYS "webauthn:challenge:*"

# Powinien pokazać klucz z challenge token
# Sprawdź TTL (powinien być ~300 sekund)
docker exec gear-stack-redis redis-cli TTL "webauthn:challenge:CHALLENGE_TOKEN"
```

#### Krok 3: Dokończ rejestrację

Po dokończeniu rejestracji (z prawdziwym WebAuthn credential), challenge powinien zostać usunięty z Redis (one-time use).

```bash
# Sprawdź, czy challenge został usunięty
docker exec gear-stack-redis redis-cli KEYS "webauthn:challenge:*"

# Powinno być puste (challenge został "skonsumowany")
```

### 4. Test TTL (automatyczne wygasanie)

```bash
# Ustaw test key z TTL 10 sekund
docker exec gear-stack-redis redis-cli SET test:key "test_value" EX 10

# Sprawdź TTL
docker exec gear-stack-redis redis-cli TTL test:key

# Poczekaj 10 sekund i sprawdź ponownie
sleep 11
docker exec gear-stack-redis redis-cli GET test:key
# Powinno zwrócić (nil) - klucz wygasł
```

## 🔍 Monitorowanie Redis

### Real-time monitoring

```bash
# Monitor wszystkich komend Redis w czasie rzeczywistym
docker exec -it gear-stack-redis redis-cli MONITOR

# Statystyki Redis
docker exec gear-stack-redis redis-cli INFO stats
```

### Sprawdź użycie pamięci

```bash
docker exec gear-stack-redis redis-cli INFO memory
```

### Sprawdź aktywne połączenia

```bash
docker exec gear-stack-redis redis-cli CLIENT LIST
```

## 🐛 Debugowanie

### Problem: Aplikacja nie może połączyć się z Redis

1. Sprawdź, czy Redis działa:
```bash
docker ps | grep redis
docker logs gear-stack-redis
```

2. Sprawdź zmienną REDIS_URL w kontenerze:
```bash
docker exec gear-stack-app env | grep REDIS
```

3. Sprawdź logi aplikacji:
```bash
docker logs gear-stack-app --tail 50 | grep -i redis
```

### Problem: Token nie jest blacklistowany

1. Sprawdź logi podczas wylogowania:
```bash
docker logs gear-stack-app -f
# Wykonaj logout w innym terminalu
```

2. Sprawdź, czy token ma pole 'exp':
```bash
# Zdekoduj JWT token na https://jwt.io/
# Sprawdź, czy ma pole "exp" (expiration)
```

### Problem: Challenge nie jest przechowywany

1. Sprawdź, czy challenge_store jest zainicjalizowany:
```bash
docker logs gear-stack-app | grep "challenge store"
```

2. Sprawdź konfigurację Redis:
```bash
docker exec gear-stack-app python -c "
from app.core.config import settings
print(f'Redis URL: {settings.redis.url}')
print(f'Challenge prefix: {settings.redis.webauthn_challenge_prefix}')
print(f'Challenge TTL: {settings.redis.webauthn_challenge_ttl}')
"
```

## 📊 Oczekiwane zachowanie

### Token Blacklist
- ✅ Token dodawany do blacklist po `/logout`
- ✅ Token dodawany do blacklist po usunięciu konta
- ✅ Blacklistowany token wygasa po naturalnym czasie życia JWT
- ✅ Próba użycia blacklistowanego tokenu zwraca 401 Unauthorized
- ✅ Hash SHA-256 tokenu przechowywany w Redis (nie raw token)

### WebAuthn Challenge Storage
- ✅ Challenge przechowywany w Redis (nie w odpowiedzi do klienta)
- ✅ Challenge ma TTL 5 minut (300 sekund)
- ✅ Challenge usuwany po jednorazowym użyciu (atomic get+delete)
- ✅ Brak challenge w Redis po dokończeniu autentykacji/rejestracji
- ✅ Wygasły challenge nie może być użyty

## 🚀 Production Checklist

Przed wdrożeniem na produkcję:

- [ ] Redis URL skonfigurowany przez zmienną środowiskową
- [ ] Redis ma włączoną persistence (AOF)
- [ ] Redis ma skonfigurowany backup
- [ ] Redis ma ograniczenie pamięci (`maxmemory`)
- [ ] Redis ma politykę eviction (`maxmemory-policy`)
- [ ] Redis nie jest eksponowany publicznie (tylko internal network)
- [ ] Monitorowanie Redis (memory, connections, commands/sec)
- [ ] Alerty dla Redis downtime
- [ ] Testy obciążeniowe dla blacklist
- [ ] Dokumentacja procedury recovery

## 📝 Notatki

### Struktura kluczy w Redis

```
blacklist:token:{SHA256_HASH}  → "reason:timestamp"
webauthn:challenge:{TOKEN}     → {"user_id": "...", "challenge": "...", "challenge_type": "...", "created_at": "..."}
```

### TTL Strategy

- **Token Blacklist**: TTL = token.exp - now (wygasa z tokenem)
- **WebAuthn Challenge**: TTL = 300 sekund (5 minut)

### Security Notes

- Tokeny przechowywane jako SHA-256 hash (nie plaintext)
- Challenge atomic get+delete (prevents replay)
- Redis persistence z AOF (Append Only File)
- Graceful degradation jeśli Redis unavailable (warning log)
