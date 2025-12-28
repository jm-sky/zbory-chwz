# FEATURE-015: reCAPTCHA Integration

**Status**: Planned (Backend Ready, Frontend Needed)
**Priority**: Medium-High (Security)
**Created**: 2025-01-21
**Author**: Claude Code

## Overview

Enable Google reCAPTCHA v3 on frontend to complete the bot protection system. Backend infrastructure is already implemented but disabled by default. This feature will protect authentication endpoints from automated attacks.

## Motivation

- **Bot Protection**: Prevent automated registration and login attacks
- **Brute Force Prevention**: Add extra layer against credential stuffing
- **Spam Reduction**: Reduce fake account creation
- **Invisible Security**: reCAPTCHA v3 works without user interaction
- **Compliance Ready**: Industry standard for bot detection

## Current State

### Backend
- ✅ `RecaptchaSettings` in config (lines 148-165 in `app/core/config.py`)
- ✅ `verify_recaptcha()` function in `app/core/recaptcha.py`
- ✅ `@recaptcha_protected()` decorator in `app/modules/auth/decorators.py`
- ✅ Applied to login, register, forgot-password endpoints
- ✅ Environment variables configured
- ⚠️ **DISABLED by default** (`RECAPTCHA_ENABLED=false`)

### Frontend
- ✅ Environment variable added (`VITE_GOOGLE_RECAPTCHA_SITE_KEY`)
- ❌ No reCAPTCHA script loading
- ❌ No token generation logic
- ❌ No composable/hooks
- ❌ API requests don't send `recaptchaToken`

## Architecture Design

### Backend (Already Implemented)

The backend is production-ready and follows gear-stack patterns:

```python
# app/core/config.py (lines 148-165)
class RecaptchaSettings(BaseSettings):
    enabled: bool = Field(default=False)
    secret_key: str = Field(default="", validation_alias="RECAPTCHA_SECRET_KEY")
    site_key: str = Field(default="", validation_alias="RECAPTCHA_SITE_KEY")
    min_score: float = Field(default=0.5)
    verify_url: str = Field(default="https://www.google.com/recaptcha/api/siteverify")

# app/core/recaptcha.py
async def verify_recaptcha(token: str, action: str = "submit") -> dict:
    """Verify reCAPTCHA token with Google API"""
    if not settings.recaptcha.enabled:
        return {"success": True, "score": 1.0, "skipped": True}
    # ... verification logic

# app/modules/auth/decorators.py
def recaptcha_protected(action: str):
    """Decorator for endpoints requiring reCAPTCHA verification"""
    # Automatically extracts recaptchaToken from request body

# app/modules/auth/router.py
@router.post("/login")
@rate_limit("10/minute")
@recaptcha_protected("login")  # ← Already applied
async def login(...):
    pass
```

**To Enable Backend**: Set `RECAPTCHA_ENABLED=true` in `.env`

### Frontend Implementation

Following gear-stack patterns (Vue 3 + Composition API):

#### 1. Environment Configuration

Already added to `.env`:
```env
VITE_GOOGLE_RECAPTCHA_SITE_KEY=6LcAMxQsAAAAAIi3SbA6t9JMPwmw8Zbadakf4QdZ
```

Update `src/shared/config/config.ts`:
```typescript
export const config = {
  // ... existing config ...
  recaptcha: {
    siteKey: import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY ?? '',
    enabled: import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY !== undefined,
  },
}
```

#### 2. reCAPTCHA Script Loader (`src/shared/utils/recaptcha.ts`)

Create utility to load reCAPTCHA script dynamically:

```typescript
// src/shared/utils/recaptcha.ts
import { config } from '@/shared/config/config'

let recaptchaLoaded = false
let recaptchaLoadPromise: Promise<void> | null = null

/**
 * Load reCAPTCHA v3 script
 */
export function loadRecaptchaScript(): Promise<void> {
  if (recaptchaLoaded) {
    return Promise.resolve()
  }

  if (recaptchaLoadPromise) {
    return recaptchaLoadPromise
  }

  if (!config.recaptcha.enabled) {
    return Promise.resolve()
  }

  recaptchaLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://www.google.com/recaptcha/api.js?render=${config.recaptcha.siteKey}`
    script.async = true
    script.defer = true

    script.onload = () => {
      recaptchaLoaded = true
      resolve()
    }

    script.onerror = () => {
      reject(new Error('Failed to load reCAPTCHA script'))
    }

    document.head.appendChild(script)
  })

  return recaptchaLoadPromise
}

/**
 * Execute reCAPTCHA and get token
 */
export async function executeRecaptcha(action: string): Promise<string | null> {
  if (!config.recaptcha.enabled) {
    return null
  }

  try {
    await loadRecaptchaScript()

    if (!window.grecaptcha) {
      console.warn('reCAPTCHA not loaded')
      return null
    }

    return await window.grecaptcha.execute(config.recaptcha.siteKey, { action })
  } catch (error) {
    console.error('reCAPTCHA execution failed:', error)
    return null
  }
}

// Type declaration for window.grecaptcha
declare global {
  interface Window {
    grecaptcha: {
      execute: (siteKey: string, options: { action: string }) => Promise<string>
      ready: (callback: () => void) => void
    }
  }
}
```

#### 3. reCAPTCHA Composable (`src/shared/composables/useRecaptcha.ts`)

Create Vue composable following gear-stack patterns:

```typescript
import { ref } from 'vue'
import { executeRecaptcha } from '@/shared/utils/recaptcha'
import { config } from '@/shared/config/config'

export function useRecaptcha() {
  const isReady = ref(false)
  const isExecuting = ref(false)
  const error = ref<string | null>(null)

  /**
   * Get reCAPTCHA token for action
   */
  const getToken = async (action: string): Promise<string | null> => {
    if (!config.recaptcha.enabled) {
      return null
    }

    isExecuting.value = true
    error.value = null

    try {
      const token = await executeRecaptcha(action)
      isReady.value = true
      return token
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get token'
      return null
    } finally {
      isExecuting.value = false
    }
  }

  return {
    getToken,
    isReady,
    isExecuting,
    error,
    isEnabled: config.recaptcha.enabled,
  }
}
```

#### 4. Update Auth Composable/Store

If using composable pattern (like in gear-stack):

```typescript
// src/modules/auth/composables/useAuth.ts (or similar)
import { useRecaptcha } from '@/shared/composables/useRecaptcha'

export function useAuth() {
  const { getToken } = useRecaptcha()

  const login = async (email: string, password: string) => {
    // Get reCAPTCHA token before API call
    const recaptchaToken = await getToken('login')

    // Make API request with token
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        recaptchaToken, // ← Add token to request
      }),
    })

    return response.json()
  }

  const register = async (email: string, password: string, name: string) => {
    const recaptchaToken = await getToken('register')

    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        name,
        recaptchaToken,
      }),
    })

    return response.json()
  }

  return {
    login,
    register,
    // ... other methods
  }
}
```

If using Pinia store pattern:

```typescript
// src/modules/auth/store/useAuthStore.ts
import { defineStore } from 'pinia'
import { useRecaptcha } from '@/shared/composables/useRecaptcha'

export const useAuthStore = defineStore('auth', () => {
  const { getToken } = useRecaptcha()

  const login = async (email: string, password: string) => {
    const recaptchaToken = await getToken('login')

    // API call with recaptchaToken
    // ...
  }

  return {
    login,
    // ...
  }
})
```

#### 5. Update API Schemas

Add `recaptchaToken` to request schemas:

```typescript
// src/modules/auth/types/index.ts (or similar)

export interface LoginRequest {
  email: string
  password: string
  recaptchaToken?: string | null  // Optional for backward compatibility
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
  recaptchaToken?: string | null
}

export interface ForgotPasswordRequest {
  email: string
  recaptchaToken?: string | null
}
```

#### 6. reCAPTCHA Badge Styling (Optional)

Add CSS to position or hide the reCAPTCHA badge:

```css
/* src/assets/styles/recaptcha.css */

/* Position badge in bottom-right */
.grecaptcha-badge {
  visibility: visible;
  z-index: 1000;
}

/* Or hide it (you must show reCAPTCHA notice in your UI) */
.grecaptcha-badge {
  visibility: hidden;
}
```

If hiding badge, add notice to footer:

```vue
<!-- src/components/layout/Footer.vue -->
<template>
  <footer>
    <p class="text-xs text-muted-foreground">
      This site is protected by reCAPTCHA and the Google
      <a href="https://policies.google.com/privacy">Privacy Policy</a> and
      <a href="https://policies.google.com/terms">Terms of Service</a> apply.
    </p>
  </footer>
</template>
```

#### 7. App Initialization

Load reCAPTCHA on app startup:

```typescript
// src/main.ts
import { createApp } from 'vue'
import App from './App.vue'
import { loadRecaptchaScript } from '@/shared/utils/recaptcha'

const app = createApp(App)

// Load reCAPTCHA script early
loadRecaptchaScript().catch(console.error)

app.mount('#app')
```

## Environment Variables

### Backend `.env`

```env
# Enable reCAPTCHA
RECAPTCHA_ENABLED=true
RECAPTCHA_SECRET_KEY=6Lxxxxxxxxxxxxxxxxxxxxxxxxxx
RECAPTCHA_SITE_KEY=6Lyyyyyyyyyyyyyyyyyyyyyyyyyyyy
RECAPTCHA_MIN_SCORE=0.5
```

### Frontend `.env`

```env
# reCAPTCHA (public site key)
VITE_GOOGLE_RECAPTCHA_SITE_KEY=6Lyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

## Score Thresholds

reCAPTCHA v3 returns a score from 0.0 (bot) to 1.0 (human). Recommended thresholds:

- **Login**: `0.3` - Lower threshold (reduce false positives)
- **Register**: `0.5` - Medium threshold (balance security/UX)
- **Forgot Password**: `0.5` - Medium threshold
- **Critical Actions**: `0.7` - Higher threshold

Configure per-endpoint in backend:

```python
@recaptcha_protected("register")  # Uses default min_score from config
async def register(...):
    pass

# Or customize:
@recaptcha_protected("login", min_score=0.3)  # Custom threshold
async def login(...):
    pass
```

## Security Considerations

1. **Token Single-Use**: reCAPTCHA tokens expire quickly
2. **Action Verification**: Backend verifies action matches
3. **Score Validation**: Configurable minimum score threshold
4. **Fallback Mode**: Works without breaking if disabled
5. **Rate Limiting**: reCAPTCHA complements rate limiting (both enabled)
6. **HTTPS Required**: reCAPTCHA requires HTTPS in production

## Testing Strategy

### Development Testing

```typescript
// Mock reCAPTCHA in development
if (import.meta.env.DEV) {
  window.grecaptcha = {
    execute: async () => 'dev-token',
    ready: (cb) => cb(),
  }
}
```

### E2E Testing

```typescript
// Disable reCAPTCHA in test environment
// .env.test
VITE_GOOGLE_RECAPTCHA_SITE_KEY=

// Or use reCAPTCHA test keys:
// Site key: 6Lexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
// Secret:   6Leyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

### Backend Tests

```python
# test_recaptcha.py
async def test_recaptcha_disabled():
    # Test with RECAPTCHA_ENABLED=false
    result = await verify_recaptcha("")
    assert result["success"] is True

async def test_recaptcha_verification():
    # Mock httpx response
    # Test score validation
    # Test action verification
```

## Implementation Phases

### Phase 1: Core Utils (1 hour)
1. Create `recaptcha.ts` utility
2. Add type declarations
3. Update config.ts

### Phase 2: Composable (1 hour)
1. Create `useRecaptcha` composable
2. Add error handling
3. Write unit tests

### Phase 3: Integration (2 hours)
1. Update auth composable/store
2. Add token to API requests
3. Update TypeScript types
4. Test with backend

### Phase 4: UI/UX (1 hour)
1. Add loading states
2. Handle errors gracefully
3. Style reCAPTCHA badge
4. Add privacy notice

### Phase 5: Testing (1 hour)
1. E2E testing with backend
2. Test score thresholds
3. Test error scenarios
4. Test disabled state

**Total Estimated Time**: 6 hours

## Backend Endpoints Protected

Once enabled, these endpoints are protected:

- `POST /auth/register` - Action: `register`
- `POST /auth/login` - Action: `login`
- `POST /auth/forgot-password` - Action: `forgot_password`

Future endpoints can easily add protection:

```python
@router.post("/contact")
@recaptcha_protected("contact")
async def contact_form(...):
    pass
```

## Alternative: Vue Package Approach

If preferred, use `vue-recaptcha-v3` package instead:

```bash
pnpm add vue-recaptcha-v3
```

```typescript
// src/main.ts
import { VueReCaptcha } from 'vue-recaptcha-v3'

app.use(VueReCaptcha, {
  siteKey: config.recaptcha.siteKey,
  loaderOptions: {
    autoHideBadge: true,
  },
})

// In component:
import { useReCaptcha } from 'vue-recaptcha-v3'

const { executeRecaptcha } = useReCaptcha()
const token = await executeRecaptcha('login')
```

**Recommendation**: Use custom implementation (lighter, more control)

## Performance Considerations

- **Lazy Loading**: Script loaded on demand, not blocking initial render
- **Cache**: Script loaded once, reused for all actions
- **Non-blocking**: Token generation happens in background
- **Size**: reCAPTCHA script is ~40KB (minified + gzipped)

## Rollout Strategy

1. **Development**: Test with low scores (0.3)
2. **Staging**: Monitor score distribution
3. **Production Soft Launch**: Enable but log-only mode
4. **Production Hard Launch**: Enforce blocking
5. **Monitor**: Track false positive rate
6. **Adjust**: Tune score thresholds based on data

## Monitoring & Debugging

Add logging to track reCAPTCHA performance:

```typescript
// src/shared/utils/recaptcha.ts
export async function executeRecaptcha(action: string): Promise<string | null> {
  try {
    const token = await window.grecaptcha.execute(...)

    // Optional: Send to analytics
    console.debug('[reCAPTCHA] Token generated', { action })

    return token
  } catch (error) {
    // Track failures
    console.error('[reCAPTCHA] Failed', { action, error })
    return null
  }
}
```

## Future Enhancements

- **reCAPTCHA Enterprise**: Upgrade for advanced features
- **Custom Challenges**: Add v2 checkbox for low scores
- **A/B Testing**: Test score thresholds
- **Analytics**: Track bot detection rates
- **Adaptive Scoring**: Adjust thresholds by endpoint

## Resources

- [reCAPTCHA v3 Documentation](https://developers.google.com/recaptcha/docs/v3)
- [Score Interpretation Guide](https://developers.google.com/recaptcha/docs/v3#interpreting_the_score)
- Company Hub implementation: `/home/madeyskij/projects/company-hub/frontend/src/lib/hooks/useRecaptcha.ts`
- Backend implementation: `/home/madeyskij/projects/gear-stack/backend/app/core/recaptcha.py`

## Success Criteria

- ✅ reCAPTCHA loads without errors
- ✅ Tokens generated on auth actions
- ✅ Backend accepts and validates tokens
- ✅ No user friction (invisible verification)
- ✅ False positive rate < 1%
- ✅ Page load time increase < 200ms
