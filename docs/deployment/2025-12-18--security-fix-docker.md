# Security Fix - Securing Database Services

**Created:** 2025-12-18
**Priority:** CRITICAL
**Status:** Action Required

## Problem

Database services (PostgreSQL, Redis) are exposed to public internet despite firewall rules, because **Docker bypasses ufw/iptables**.

## Why Docker Bypasses Firewall

Docker manipulates iptables directly with higher priority rules, effectively bypassing ufw. When you expose ports like:

```yaml
ports:
  - "5432:5432"  # Exposes to 0.0.0.0:5432 (ALL interfaces)
```

Docker adds iptables rules that allow this traffic **before** ufw rules are checked.

---

## Solution 1: Bind to Localhost (RECOMMENDED)

Change all database port bindings to localhost only:

### Update docker-compose.dev.yml

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"  # ✅ Only accessible from localhost
    # ... rest of config

  redis:
    ports:
      - "127.0.0.1:6379:6379"  # ✅ Only accessible from localhost
    # ... rest of config
```

### Update .env

Add Redis authentication:
```bash
# Add to .env
REDIS_PASSWORD=<generate-strong-password>
```

Generate password:
```bash
openssl rand -base64 32
```

### Update docker-compose for Redis auth

```yaml
redis:
  ports:
    - "127.0.0.1:6379:6379"
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
  environment:
    - REDIS_PASSWORD=${REDIS_PASSWORD}
```

### Update application connection string

```python
# In .env or docker-compose
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

---

## Solution 2: Remove Port Forwarding for Production (BEST)

For production, **don't expose database ports at all**:

### Create docker-compose.prod.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:17-alpine
    container_name: gear-stack-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - gear_stack_postgres_data:/var/lib/postgresql/data
    # ✅ NO ports section - only accessible within Docker network
    networks:
      - gearstack-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis/redis-stack:latest
    container_name: gear-stack-redis
    restart: unless-stopped
    # ✅ NO ports section - only accessible within Docker network
    command: >
      redis-server
      --appendonly yes
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    volumes:
      - gear_stack_redis_data:/data
    networks:
      - gearstack-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: gear-stack-app
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    ports:
      - "127.0.0.1:8000:8000"  # Only expose app to localhost (Caddy will proxy)
    volumes:
      - gear_stack_uploads:/app/uploads
    networks:
      - gearstack-network

networks:
  gearstack-network:
    driver: bridge
    internal: false  # Set to true for maximum isolation (app won't reach internet)

volumes:
  gear_stack_postgres_data:
  gear_stack_redis_data:
  gear_stack_uploads:
```

---

## Solution 3: Docker + ufw Integration (Advanced)

If you need port forwarding but want ufw protection:

### Option A: Configure Docker to use ufw

Edit `/etc/docker/daemon.json`:

```json
{
  "iptables": false
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

**WARNING:** This disables Docker's iptables management. You'll need to manually manage all networking.

### Option B: Use docker-ufw-fix script

Install docker-ufw script to make Docker respect ufw:
```bash
# Install chaifeng/ufw-docker
curl -fsSL https://raw.githubusercontent.com/chaifeng/ufw-docker/master/install.sh | sudo sh
```

---

## Verification Steps

### 1. Check what's listening on public interfaces

```bash
# Check all listening ports
ss -tlnp | grep -E ":5432|:6379|:6399|:8000"

# Should show 127.0.0.1 only for databases:
# ✅ LISTEN 0  4096  127.0.0.1:5432   0.0.0.0:*
# ✅ LISTEN 0  4096  127.0.0.1:6379   0.0.0.0:*
# ❌ LISTEN 0  4096  0.0.0.0:5432     0.0.0.0:*  (BAD!)
```

### 2. Test from external network

From a different machine:
```bash
# Should timeout/refuse connection:
telnet <VPS_IP> 5432
telnet <VPS_IP> 6379
```

### 3. Test from localhost

```bash
# Should connect successfully:
psql -h 127.0.0.1 -U backend -d backend
redis-cli -h 127.0.0.1 -p 6379
```

---

## Implementation Plan

### Step 1: Backup Current State
```bash
cd /home/madeyskij/projects/gear-stack/backend
docker compose -f docker-compose.dev.yml down
sudo cp -r /var/lib/docker/volumes /var/lib/docker/volumes.backup
```

### Step 2: Update Configuration

1. Edit `docker-compose.dev.yml` - bind ports to 127.0.0.1
2. Add `REDIS_PASSWORD` to `.env`
3. Update `REDIS_URL` in `.env` to include password

### Step 3: Apply Changes

```bash
# Restart services
docker compose -f docker-compose.dev.yml up -d

# Check logs
docker compose -f docker-compose.dev.yml logs -f
```

### Step 4: Verify Security

```bash
# Check listening ports
ss -tlnp | grep -E ":5432|:6379"

# Should show 127.0.0.1 only!
```

### Step 5: Test from External IP

From another machine, verify ports are NOT accessible:
```bash
nc -zv <VPS_IP> 5432  # Should fail
nc -zv <VPS_IP> 6379  # Should fail
```

---

## Remote Database Access (When Needed)

If you need remote access for development/admin, use **SSH tunneling**:

```bash
# Forward PostgreSQL through SSH
ssh -L 5432:127.0.0.1:5432 user@<VPS_IP>

# Now connect to localhost:5432 on your machine
psql -h 127.0.0.1 -U backend -d backend
```

For Redis:
```bash
ssh -L 6379:127.0.0.1:6379 user@<VPS_IP>
redis-cli -h 127.0.0.1
```

---

## Firewall Configuration (Defense in Depth)

Even with localhost binding, configure firewall as backup:

```bash
# Reset ufw (if needed)
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Enable
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

---

## Additional Security Measures

### 1. Fail2ban for SSH Protection

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. PostgreSQL - Disable Remote Root

Edit `postgresql.conf` or use environment:
```yaml
environment:
  - POSTGRES_HOST_AUTH_METHOD=scram-sha-256
```

### 3. Redis Security Hardening

```bash
# In redis command:
--rename-command FLUSHDB ""
--rename-command FLUSHALL ""
--rename-command CONFIG ""
--disable-default-user yes
```

### 4. Regular Security Audits

```bash
# Check open ports
sudo ss -tlnp

# Check Docker exposed ports
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Check for 0.0.0.0 bindings
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep "0.0.0.0"
```

---

## Checklist

- [ ] Backup current Docker volumes
- [ ] Update `docker-compose.dev.yml` - bind ports to 127.0.0.1
- [ ] Generate strong REDIS_PASSWORD
- [ ] Add REDIS_PASSWORD to .env
- [ ] Update REDIS_URL with password
- [ ] Update redis command to use --requirepass
- [ ] Restart Docker services
- [ ] Verify ports only listen on 127.0.0.1
- [ ] Test external access is blocked
- [ ] Test internal access works
- [ ] Create docker-compose.prod.yml without port forwarding
- [ ] Document SSH tunneling procedure for remote access
- [ ] Configure ufw firewall
- [ ] Install fail2ban
- [ ] Rotate all credentials (PostgreSQL, Redis, SECRET_KEY, AI keys)
- [ ] Set up monitoring/alerting
- [ ] Document incident for future reference

---

## Emergency Rollback

If something breaks:

```bash
cd /home/madeyskij/projects/gear-stack/backend
docker compose -f docker-compose.dev.yml down
git checkout docker-compose.dev.yml
docker compose -f docker-compose.dev.yml up -d
```

---

## References

- [Docker and ufw](https://github.com/chaifeng/ufw-docker)
- [Redis Security](https://redis.io/docs/management/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [Docker Network Security](https://docs.docker.com/network/network-tutorial-standalone/)
