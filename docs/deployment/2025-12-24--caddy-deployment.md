# Caddy Configuration Deployment Guide

**Last Updated:** 2025-12-24

This guide explains how to deploy the Caddy configuration for Gear Stack with enhanced security headers.

## 📋 Overview

The Caddy configuration includes:
- ✅ Content Security Policy (CSP) with Google reCaptcha support
- ✅ HTTP Strict Transport Security (HSTS) with preload
- ✅ Anti-clickjacking headers (X-Frame-Options)
- ✅ MIME sniffing protection
- ✅ XSS protection headers
- ✅ Referrer policy
- ✅ Permissions policy (blocks geolocation, microphone, camera)
- ✅ Server fingerprinting protection
- ✅ Optimized caching for static assets
- ✅ SPA routing support
- ✅ API reverse proxy to FastAPI backend

## 🚀 Deployment Steps

### 1. Copy Configuration File

```bash
# From your local machine or project directory
sudo cp docs/deployment/gear-stack.caddy /etc/caddy/sites-available/gear-stack.caddy
```

### 2. Verify File Permissions

```bash
# Ensure Caddy can read the file
sudo chown caddy:caddy /etc/caddy/sites-available/gear-stack.caddy
sudo chmod 644 /etc/caddy/sites-available/gear-stack.caddy
```

### 3. Create Symlink (if not exists)

```bash
# Enable the site by creating a symlink
sudo ln -sf /etc/caddy/sites-available/gear-stack.caddy /etc/caddy/sites-enabled/gear-stack.caddy
```

### 4. Validate Configuration

```bash
# Test Caddy configuration syntax
caddy validate --config /etc/caddy/Caddyfile

# Or as root if needed
sudo caddy validate --config /etc/caddy/Caddyfile
```

Expected output:
```
{"level":"info","msg":"using config from file","file":"/etc/caddy/Caddyfile"}
{"level":"info","msg":"adapted config to JSON","adapter":"caddyfile"}
Valid configuration
```

### 5. Reload Caddy

```bash
# Reload Caddy to apply changes (zero-downtime)
sudo caddy reload --config /etc/caddy/Caddyfile

# Alternative: restart Caddy service
sudo systemctl reload caddy
```

### 6. Verify Deployment

```bash
# Check Caddy service status
sudo systemctl status caddy

# Test security headers
curl -I https://gear-stack.ovh | grep -E "(Content-Security-Policy|X-Frame-Options|Strict-Transport-Security)"
```

Expected headers:
```
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://www.google.com https://www.gstatic.com; ...
```

## 🧪 Testing

### Online Security Header Tests

Test your deployment with these online tools:

1. **Security Headers:**
   - https://securityheaders.com
   - Check for A+ rating

2. **Mozilla Observatory:**
   - https://observatory.mozilla.org
   - Verify all security headers

3. **CSP Evaluator (Google):**
   - https://csp-evaluator.withgoogle.com
   - Validate CSP policy

### Manual Testing

```bash
# Test CSP header
curl -I https://gear-stack.ovh | grep -i "content-security-policy"

# Test HSTS
curl -I https://gear-stack.ovh | grep -i "strict-transport-security"

# Test X-Frame-Options
curl -I https://gear-stack.ovh | grep -i "x-frame-options"

# Test full response headers
curl -I https://gear-stack.ovh

# Test API proxy
curl -I https://gear-stack.ovh/api/health
```

### Browser Testing

1. Open https://gear-stack.ovh in browser
2. Open DevTools (F12)
3. Go to Console tab
4. Check for CSP violations (should be none)
5. Go to Network tab
6. Reload page
7. Check response headers for security headers

## 🔍 Troubleshooting

### Configuration Validation Fails

```bash
# Check syntax errors
caddy validate --config /etc/caddy/Caddyfile

# Check Caddy logs
sudo journalctl -u caddy -f

# Check for syntax issues in the Caddyfile
sudo caddy fmt /etc/caddy/Caddyfile --overwrite
```

### Headers Not Appearing

```bash
# Ensure Caddy is running
sudo systemctl status caddy

# Check if site is enabled
ls -la /etc/caddy/sites-enabled/ | grep gear-stack

# Verify symlink is correct
readlink -f /etc/caddy/sites-enabled/gear-stack.caddy

# Reload Caddy
sudo caddy reload --config /etc/caddy/Caddyfile
```

### CSP Blocking Resources

If CSP blocks legitimate resources:

1. Open browser DevTools Console
2. Look for CSP violation messages
3. Identify the blocked resource domain
4. Update CSP directive in gear-stack.caddy
5. Reload Caddy configuration

Example: Adding a new script source
```caddyfile
# Before
script-src 'self' 'unsafe-inline' https://www.google.com https://www.gstatic.com

# After (if you need to add example.com)
script-src 'self' 'unsafe-inline' https://www.google.com https://www.gstatic.com https://example.com
```

### Backend API Not Working

```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Check Caddy proxy logs
sudo journalctl -u caddy -f

# Test direct backend access
docker ps | grep gear-stack-app
docker logs gear-stack-app
```

## 📝 Configuration Reference

### CSP Directives Explained

| Directive | Purpose | Current Value |
|-----------|---------|---------------|
| `default-src` | Default policy for all resource types | `'self'` |
| `script-src` | JavaScript execution sources | `'self' 'unsafe-inline' blob: https://www.google.com https://www.gstatic.com` |
| `style-src` | CSS sources | `'self' 'unsafe-inline'` |
| `img-src` | Image sources | `'self' data: https:` |
| `font-src` | Font sources | `'self' data:` |
| `connect-src` | XHR, WebSocket, EventSource | `'self' https://*.gear-stack.ovh https://www.google.com https://*.sentry.io` |
| `worker-src` | Web Workers | `'self' blob:` |
| `frame-src` | iframe sources (for reCaptcha) | `'self' https://www.google.com https://www.gstatic.com` |
| `frame-ancestors` | Who can embed this site | `'none'` (prevents clickjacking) |
| `base-uri` | Allowed base URLs | `'self'` |
| `form-action` | Form submission targets | `'self'` |

**Note:** `'unsafe-inline'` is currently required for Vue.js inline styles and some third-party scripts. In future iterations, consider using CSP nonces for improved security.

### Cache Control Strategy

| Resource Type | Cache Duration | Rationale |
|---------------|---------------|-----------|
| Hashed assets (`/assets/*.js`, `*.css`) | 1 year (immutable) | Vite hashes filenames; safe to cache forever |
| HTML files | No cache | Ensures users get latest app version |
| Static assets (images, fonts) | 1 hour | Balance between performance and freshness |

## 🔄 Updating Configuration

When you need to update the Caddy configuration:

1. Edit `docs/deployment/gear-stack.caddy` in the project
2. Test locally if possible
3. Copy to server: `sudo cp docs/deployment/gear-stack.caddy /etc/caddy/sites-available/gear-stack.caddy`
4. Validate: `sudo caddy validate --config /etc/caddy/Caddyfile`
5. Reload: `sudo caddy reload --config /etc/caddy/Caddyfile`
6. Test: Verify headers with curl or browser DevTools

## 📚 References

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Header Directive](https://caddyserver.com/docs/caddyfile/directives/header)
- [Reverse Proxy Directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Content Security Policy Reference](https://content-security-policy.com/)
- [Google reCaptcha CSP Guide](https://developers.google.com/recaptcha/docs/faq#im-using-content-security-policy-csp-on-my-website.-how-can-i-configure-it-to-work-with-recaptcha)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)

## 🆘 Support

If you encounter issues:

1. Check Caddy logs: `sudo journalctl -u caddy -f`
2. Verify backend is running: `docker ps`
3. Test backend directly: `curl http://localhost:8000/api/health`
4. Check DNS resolution: `dig gear-stack.ovh`
5. Verify TLS certificates: `sudo caddy list-certificates`

For security header issues, use online testing tools listed in the Testing section.
