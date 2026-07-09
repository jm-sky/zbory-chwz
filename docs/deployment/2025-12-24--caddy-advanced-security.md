# Caddy Advanced Security Features

**Last Updated:** 2025-12-24
**Status:** 📝 Implementation Guide

This document outlines advanced security features that can be added to Caddy using third-party modules.

## 📋 Overview

The standard Caddy binary includes excellent security features (HTTPS, headers), but advanced features like rate limiting and WAF require custom builds using **xcaddy**.

## 🔧 Building Custom Caddy with xcaddy

### Installation

```bash
# Install xcaddy
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Or download prebuilt binary
# https://github.com/caddyserver/xcaddy/releases
```

### Build Caddy with Security Modules

```bash
# Build Caddy with rate limiting and WAF
xcaddy build \
  --with github.com/mholt/caddy-ratelimit \
  --with github.com/corazawaf/coraza-caddy

# The built binary will be in the current directory
# Replace system Caddy
sudo systemctl stop caddy
sudo cp caddy /usr/bin/caddy
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/caddy
sudo systemctl start caddy
```

**Reference:**
- [xcaddy GitHub](https://github.com/caddyserver/xcaddy)
- [Caddy Rate Limit Module](https://github.com/mholt/caddy-ratelimit)
- [Coraza WAF for Caddy](https://github.com/corazawaf/coraza-caddy)

## 🛡️ Rate Limiting Configuration

### Purpose
Protects against brute force attacks, DDoS, and API abuse.

### Installation
```bash
xcaddy build --with github.com/mholt/caddy-ratelimit
```

### Configuration

Add to `gear-stack.caddy`:

```caddyfile
{
  # Global order directive - rate_limit runs before basic auth
  order rate_limit before basicauth
}

gear-stack.ovh {
  # ... existing config ...

  # Rate limiting configuration
  rate_limit {
    # Zone for API endpoints - strict limits
    zone api_zone {
      key {http.request.remote.host}
      events 60      # 60 requests
      window 1m      # per minute
      match {
        path /api/*
      }
    }

    # Zone for login endpoints - very strict
    zone auth_zone {
      key {http.request.remote.host}
      events 5       # 5 attempts
      window 15m     # per 15 minutes
      match {
        path /api/auth/login
        path /api/auth/register
      }
    }

    # Zone for general web traffic
    zone web_zone {
      key {http.request.remote.host}
      events 120     # 120 requests
      window 1m      # per minute
    }

    # Optional: Distributed rate limiting (if multiple Caddy instances)
    # distributed {
    #   read_interval 1s
    #   write_interval 1s
    #   purge_age 1h
    # }

    # Add rate limit info to logs
    log_key
  }

  # ... rest of config ...
}
```

### Configuration Options

| Parameter | Description | Example |
|-----------|-------------|---------|
| `key` | Identifier for rate limiting (usually IP) | `{http.request.remote.host}` |
| `events` | Max number of requests | `60` |
| `window` | Time window | `1m`, `5m`, `1h` |
| `match` | Request matcher (path, method, etc.) | `path /api/*` |
| `distributed` | Sync across multiple instances | See example above |

### Testing

```bash
# Test rate limiting
for i in {1..70}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://gear-stack.ovh/api/health
done

# Should see:
# 200
# 200
# ...
# 429 (Too Many Requests)
```

**References:**
- [Caddy Rate Limit Documentation](https://caddyserver.com/docs/modules/http.handlers.rate_limit)
- [mholt/caddy-ratelimit GitHub](https://github.com/mholt/caddy-ratelimit)

## 🔥 Web Application Firewall (Coraza WAF)

### Purpose
Protects against OWASP Top 10 vulnerabilities (SQL injection, XSS, etc.).

### Installation

```bash
xcaddy build --with github.com/corazawaf/coraza-caddy
```

### Configuration

Create `coraza.conf`:

```bash
# /etc/caddy/coraza/coraza.conf
SecRuleEngine On
SecRequestBodyAccess On
SecResponseBodyAccess Off

# Audit logging
SecAuditEngine RelevantOnly
SecAuditLog /var/log/caddy/waf-audit.log
SecAuditLogFormat JSON

# OWASP Core Rule Set
Include /etc/caddy/coraza/crs/crs-setup.conf
Include /etc/caddy/coraza/crs/rules/*.conf
```

Add to `Caddyfile` (global section):

```caddyfile
{
  # CRITICAL: order directive MUST be first
  order coraza_waf first
}

gear-stack.ovh {
  # WAF Configuration
  coraza_waf {
    # Load OWASP Core Rule Set
    load_owasp_crs

    directives {
      # Enable rule engine
      SecRuleEngine On

      # Request body inspection
      SecRequestBodyAccess On
      SecRequestBodyLimit 10485760  # 10MB

      # Paranoia level (1-4, higher = stricter)
      # Start with 1, gradually increase
      SecAction "id:900000,phase:1,nolog,pass,t:none,setvar:tx.paranoia_level=1"

      # Custom rules

      # Block SQL injection attempts
      SecRule ARGS "@detectSQLi" \
        "id:1001,phase:2,deny,status:403,msg:'SQL Injection Detected',\
        logdata:'Matched Data: %{MATCHED_VAR} found within %{MATCHED_VAR_NAME}'"

      # Block XSS attempts
      SecRule ARGS "@detectXSS" \
        "id:1002,phase:2,deny,status:403,msg:'XSS Attack Detected',\
        logdata:'Matched Data: %{MATCHED_VAR} found within %{MATCHED_VAR_NAME}'"

      # Rate limiting (basic WAF-level)
      SecAction "id:1003,phase:1,pass,setvar:ip.requests=+1,expirevar:ip.requests=60"
      SecRule IP:REQUESTS "@gt 100" \
        "id:1004,phase:1,deny,status:429,msg:'Rate limit exceeded'"
    }
  }

  # ... rest of config ...
}
```

### Download OWASP Core Rule Set

```bash
# Download CRS
cd /etc/caddy
sudo mkdir -p coraza/crs
cd coraza/crs
sudo wget https://github.com/coreruleset/coreruleset/archive/v4.0.0.tar.gz
sudo tar -xzvf v4.0.0.tar.gz --strip-components=1
sudo cp crs-setup.conf.example crs-setup.conf

# Configure CRS
sudo nano crs-setup.conf
# Set paranoia level: SecAction "id:900000,phase:1,nolog,pass,t:none,setvar:tx.paranoia_level=1"
```

### Testing WAF

```bash
# Test SQL injection blocking
curl "https://gear-stack.ovh/api/containers?id=1' OR '1'='1"
# Should return: 403 Forbidden

# Test XSS blocking
curl "https://gear-stack.ovh/api/search?q=<script>alert('xss')</script>"
# Should return: 403 Forbidden

# Test normal request (should work)
curl https://gear-stack.ovh/api/health
# Should return: 200 OK
```

### Monitoring WAF Logs

```bash
# View WAF audit log
sudo tail -f /var/log/caddy/waf-audit.log | jq

# View Caddy error log for WAF events
sudo journalctl -u caddy -f | grep -i coraza
```

**References:**
- [Coraza Caddy GitHub](https://github.com/corazawaf/coraza-caddy)
- [OWASP Coraza Project](https://owasp.org/www-project-coraza-web-application-firewall/)
- [Using Caddy with OWASP Core Ruleset](https://wyattp.us/projects/caddywaf.html)

## 🌐 CORS Configuration (No xcaddy Required)

Caddy can handle CORS without additional modules.

### Current Backend CORS Settings

From `backend/.env`:
```bash
CORS_ORIGINS=["https://gear-stack.ovh","https://api.gear-stack.ovh"]
CORS_CREDENTIALS="True"
```

### Caddy CORS Configuration (Optional)

If you want Caddy to handle CORS (instead of backend):

```caddyfile
gear-stack.ovh {
  # Handle OPTIONS preflight requests
  @options {
    method OPTIONS
  }

  handle @options {
    header {
      Access-Control-Allow-Origin "https://gear-stack.ovh"
      Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
      Access-Control-Allow-Headers "Content-Type, Authorization, X-CSRF-Token"
      Access-Control-Allow-Credentials "true"
      Access-Control-Max-Age "86400"
    }
    respond 204
  }

  # Add CORS headers to all responses
  header {
    Access-Control-Allow-Origin "https://gear-stack.ovh"
    Access-Control-Allow-Credentials "true"
  }

  # ... rest of config ...
}
```

**Note:** Currently, the FastAPI backend handles CORS, which is the recommended approach for API-first applications.

**References:**
- [Caddy CORS Proxy Guide](https://4bit.dev/posts/caddy-cors-proxy/)
- [Caddy Community CORS Discussion](https://caddy.community/t/cors-allow-origin-with-reverse-proxy/19355)

## 📊 Comparison: Standard vs Advanced Caddy

| Feature | Standard Caddy | With xcaddy Modules |
|---------|---------------|---------------------|
| **HTTPS/TLS** | ✅ Automatic | ✅ Automatic |
| **Security Headers** | ✅ Manual config | ✅ Manual config |
| **CORS** | ✅ Manual config | ✅ Manual config |
| **Rate Limiting** | ❌ Not available | ✅ Available |
| **WAF (OWASP CRS)** | ❌ Not available | ✅ Available |
| **DDoS Protection** | ⚠️ Basic | ✅ Advanced |
| **SQL Injection Block** | ❌ Not available | ✅ Available |
| **XSS Protection** | ⚠️ Header only | ✅ Content inspection |

## 🚀 Recommended Implementation Path

### Phase 1: Current (No xcaddy) ✅
- [x] Security headers (CSP, HSTS, X-Frame-Options)
- [x] HTTPS with automatic certificates
- [x] Reverse proxy with header forwarding
- [x] Backend rate limiting (FastAPI)
- [x] Backend CORS (FastAPI)

### Phase 2: Enhanced Security (xcaddy) 🔄 Planned
- [ ] Build Caddy with rate limiting module
- [ ] Configure per-endpoint rate limits
- [ ] Test rate limiting in staging
- [ ] Deploy to production

### Phase 3: WAF Implementation (xcaddy) 🔄 Planned
- [ ] Build Caddy with Coraza WAF
- [ ] Download OWASP Core Rule Set
- [ ] Configure WAF with paranoia level 1
- [ ] Test WAF with common attacks
- [ ] Monitor and tune false positives
- [ ] Gradually increase paranoia level

### Phase 4: Advanced Monitoring 🔄 Planned
- [ ] Integrate WAF logs with Sentry
- [ ] Set up alerting for attack patterns
- [ ] Configure automated blocking
- [ ] Create WAF dashboard

## 💡 Decision Matrix: When to Use xcaddy

| Scenario | Use Standard Caddy | Use xcaddy |
|----------|-------------------|------------|
| **Small app, low traffic** | ✅ Sufficient | ❌ Overkill |
| **Production API, < 1000 users** | ✅ Start here | ⏳ Monitor and upgrade |
| **Production API, > 10k users** | ⚠️ Risky | ✅ Recommended |
| **Handling sensitive data** | ⚠️ Risky | ✅ Recommended |
| **E-commerce/payments** | ❌ Insufficient | ✅ Required |
| **Public API, no auth** | ❌ Insufficient | ✅ Required |
| **Internal tool, VPN only** | ✅ Sufficient | ❌ Not needed |

## 🔍 Monitoring & Metrics

### Rate Limit Metrics

```bash
# Check rate limit hits in Caddy logs
sudo journalctl -u caddy -f | grep -i "rate limit"

# Count 429 responses
sudo journalctl -u caddy --since "1 hour ago" | grep "429" | wc -l
```

### WAF Metrics

```bash
# WAF blocks
sudo grep -c "SecAction" /var/log/caddy/waf-audit.log

# Top blocked IPs
sudo cat /var/log/caddy/waf-audit.log | jq -r '.client_ip' | sort | uniq -c | sort -rn | head -10

# Top triggered rules
sudo cat /var/log/caddy/waf-audit.log | jq -r '.messages[].ruleId' | sort | uniq -c | sort -rn | head -10
```

## 📚 Additional Resources

### Official Documentation
- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddy Modules Registry](https://caddyserver.com/download)
- [xcaddy Builder](https://github.com/caddyserver/xcaddy)

### Security Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Core Rule Set](https://coreruleset.org/)
- [Coraza WAF Documentation](https://coraza.io/docs/)

### Community Resources
- [Caddy Community Forum](https://caddy.community/)
- [Caddy Security Best Practices](https://www.talkincyber.com/secure-caddy/)
- [OSS WAF Stack (Coraza + Caddy + Elastic)](https://medium.com/@jptosso/oss-waf-stack-using-coraza-caddy-and-elastic-3a715dcbf2f2)

## 🆘 Troubleshooting

### xcaddy Build Fails

```bash
# Ensure Go is installed
go version

# Update Go if needed
# https://go.dev/doc/install

# Clear Go module cache
go clean -modcache

# Try build again
xcaddy build --with github.com/mholt/caddy-ratelimit
```

### Rate Limiting Not Working

```bash
# Verify module is loaded
caddy list-modules | grep rate_limit

# Check Caddy config syntax
caddy validate --config /etc/caddy/Caddyfile

# Check logs for errors
sudo journalctl -u caddy -n 100
```

### WAF Blocking Legitimate Requests

```bash
# Check WAF logs for rule ID
sudo cat /var/log/caddy/waf-audit.log | jq '.messages[] | select(.ruleId=="<RULE_ID>")'

# Disable specific rule (add to coraza.conf)
SecRuleRemoveById <RULE_ID>

# Or lower paranoia level
SecAction "id:900000,phase:1,nolog,pass,t:none,setvar:tx.paranoia_level=1"
```

---

**Last Updated:** 2025-12-24
**Next Review:** 2026-01-24
