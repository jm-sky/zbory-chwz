# FEATURE-014: OAuth Authentication

**Status**: Planned
**Priority**: Medium
**Created**: 2025-01-21
**Author**: Claude Code

## Overview

Add OAuth authentication support to allow users to sign in with Google and GitHub accounts. This feature will complement the existing email/password authentication system.

## Motivation

- **User Convenience**: Eliminate need to create/remember passwords
- **Faster Onboarding**: Reduce friction in registration process
- **Enhanced Security**: Leverage OAuth providers' security infrastructure
- **Industry Standard**: OAuth is widely adopted and trusted

## Current State

### Backend
- ✅ OAuth environment variables configured in `.env`
- ✅ reCAPTCHA infrastructure exists (can be reused)
- ❌ No OAuth provider implementations
- ❌ No OAuth endpoints

### Frontend
- ✅ Environment variables added (`VITE_GOOGLE_OAUTH_CLIENT_ID`)
- ❌ No OAuth components
- ❌ No OAuth hooks
- ❌ No OAuth UI elements

## Architecture Design

### Backend Implementation

#### 1. OAuth Service Layer (`backend/app/core/oauth.py`)

Create a modular OAuth service following the existing patterns:

```python
# File structure matches existing core services (config.py, recaptcha.py)
from abc import ABC, abstractmethod
from pydantic import BaseModel
import httpx

class OAuthUserInfo(BaseModel):
    """Standardized OAuth user info (camelCase for API consistency)"""
    provider: str
    providerId: str
    email: str
    name: str | None = None
    avatarUrl: str | None = None

class OAuthTokenResponse(BaseModel):
    """OAuth token exchange response"""
    accessToken: str
    tokenType: str
    scope: str | None = None
    refreshToken: str | None = None

class OAuthProvider(ABC):
    """Abstract base for OAuth providers"""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate authorization URL"""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> OAuthTokenResponse:
        """Exchange code for access token"""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user information"""
        pass

class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth implementation"""
    # Uses settings.google_oauth_client_id and google_oauth_client_secret

class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth implementation (future)"""

class OAuthService:
    """Central OAuth service"""
    def __init__(self):
        self.providers = {
            "google": GoogleOAuthProvider(),
            # "github": GitHubOAuthProvider(),  # Future
        }
```

#### 2. Configuration Updates (`backend/app/core/config.py`)

Add OAuth settings following existing `RecaptchaSettings` pattern:

```python
class OAuthSettings(BaseSettings):
    """OAuth configuration"""
    model_config = _base_config

    # Google OAuth
    google_client_id: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_client_secret: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_redirect_uri: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_REDIRECT_URI"
    )

class Settings(BaseSettings):
    # ... existing settings ...
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
```

#### 3. Auth Service Updates (`backend/app/modules/auth/service.py`)

Add OAuth methods to existing `AuthService` class:

```python
class AuthService:
    # ... existing methods ...

    async def login_with_oauth(
        self,
        provider: str,
        oauth_user_info: OAuthUserInfo
    ) -> LoginResponse:
        """
        Login or register user via OAuth.

        - Check if user exists by email
        - If exists: verify OAuth provider matches or link account
        - If not exists: create new user with OAuth info
        - Generate JWT tokens
        """
        user = await self.user_repository.get_user_by_email(
            oauth_user_info.email
        )

        if not user:
            # Create new user (no password needed for OAuth users)
            user = await self.user_repository.create_oauth_user(
                email=oauth_user_info.email,
                name=oauth_user_info.name or oauth_user_info.email,
                provider=provider,
                provider_id=oauth_user_info.providerId,
                avatar_url=oauth_user_info.avatarUrl,
            )

        # Generate tokens (same as regular login)
        # Return LoginResponse
```

#### 4. Repository Updates (`backend/app/modules/auth/repositories/`)

Add OAuth-specific repository methods:

```python
# In UserRepositoryInterface
async def create_oauth_user(
    self,
    email: str,
    name: str,
    provider: str,
    provider_id: str,
    avatar_url: str | None = None
) -> User:
    """Create user via OAuth (no password)"""
    pass

async def get_user_by_oauth_provider(
    self,
    provider: str,
    provider_id: str
) -> User | None:
    """Get user by OAuth provider ID"""
    pass
```

#### 5. User Model Updates (`backend/app/modules/auth/models.py`)

Add OAuth fields to User model:

```python
class User(BaseModel):
    # ... existing fields ...
    oauthProvider: str | None = None  # 'google', 'github', etc.
    oauthProviderId: str | None = None  # Provider's user ID
    avatarUrl: str | None = None  # Profile picture URL
```

#### 6. Router Updates (`backend/app/modules/auth/router.py`)

Add OAuth endpoints following existing patterns:

```python
@router.post(
    "/oauth/auth-url",
    response_model=dict,
    summary="Get OAuth authorization URL",
    tags=["Authentication"]
)
async def get_oauth_auth_url(provider: str) -> dict:
    """
    Generate OAuth authorization URL.
    Returns: { "authUrl": "https://...", "state": "csrf-token" }
    """
    from app.core.oauth import oauth_service
    state = oauth_service.generate_state()
    auth_url = oauth_service.get_authorization_url(provider, state)
    return {"authUrl": auth_url, "state": state}

@router.post(
    "/oauth/callback",
    response_model=LoginResponse,
    summary="OAuth callback handler",
    tags=["Authentication"]
)
@rate_limit("10/minute")
@recaptcha_protected("oauth_callback")  # Optional
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    auth_service: AuthServiceDep,
    request: Request
) -> LoginResponse:
    """
    Handle OAuth callback and login/register user.
    """
    # Exchange code for token
    # Get user info from provider
    # Login/register user
    # Return tokens
```

### Frontend Implementation

#### 1. Environment Configuration

Already added to `.env`:
```env
VITE_GOOGLE_OAUTH_CLIENT_ID=946297486350-3e754ifbovdni5cac8eru6337mi28o8q.apps.googleusercontent.com
```

Update `src/shared/config/config.ts`:
```typescript
export const config = {
  // ... existing config ...
  oauth: {
    google: {
      clientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID,
    },
  },
}
```

#### 2. API Client Updates

Add OAuth methods to existing API client (if backend integration exists):

```typescript
// src/shared/api/client.ts or similar
export const authApi = {
  // ... existing methods ...

  async getOAuthAuthUrl(provider: string) {
    const response = await fetch(`${API_BASE_URL}/auth/oauth/auth-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    })
    return response.json()
  },

  async oauthCallback(provider: string, code: string, state: string) {
    const response = await fetch(`${API_BASE_URL}/auth/oauth/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, code, state }),
    })
    return response.json()
  },
}
```

#### 3. OAuth Composable (`src/shared/composables/useOAuth.ts`)

Create Vue composable following existing patterns:

```typescript
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/shared/api/client'
import { config } from '@/shared/config/config'

export function useOAuth() {
  const router = useRouter()
  const isPending = ref(false)
  const error = ref<string | null>(null)

  const initiateGoogleLogin = async () => {
    if (!config.oauth.google.enabled) {
      error.value = 'Google OAuth not configured'
      return
    }

    isPending.value = true
    error.value = null

    try {
      const { authUrl, state } = await authApi.getOAuthAuthUrl('google')

      // Store state for CSRF verification
      localStorage.setItem('oauth_state', state)

      // Redirect to Google
      window.location.href = authUrl
    } catch (err) {
      error.value = 'Failed to initiate login'
      isPending.value = false
    }
  }

  const handleCallback = async (provider: string, code: string, state: string) => {
    isPending.value = true
    error.value = null

    try {
      // Verify CSRF state
      const storedState = localStorage.getItem('oauth_state')
      if (storedState !== state) {
        throw new Error('Invalid state parameter')
      }

      // Exchange code for tokens
      const response = await authApi.oauthCallback(provider, code, state)

      // Store tokens (use existing auth store pattern)
      // Navigate to dashboard

      localStorage.removeItem('oauth_state')
      router.push('/dashboard')
    } catch (err) {
      error.value = 'Authentication failed'
      router.push('/login?error=oauth_failed')
    } finally {
      isPending.value = false
    }
  }

  return {
    initiateGoogleLogin,
    handleCallback,
    isPending,
    error,
  }
}
```

#### 4. OAuth Button Component (`src/components/auth/OAuthButton.vue`)

Create reusable button component following shadcn-vue patterns:

```vue
<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { useOAuth } from '@/shared/composables/useOAuth'

const { initiateGoogleLogin, isPending } = useOAuth()
</script>

<template>
  <Button
    variant="outline"
    size="lg"
    class="w-full"
    :disabled="isPending"
    @click="initiateGoogleLogin"
  >
    <svg class="mr-2 size-5" viewBox="0 0 24 24">
      <!-- Google icon SVG -->
    </svg>
    {{ isPending ? 'Redirecting...' : 'Continue with Google' }}
  </Button>
</template>
```

#### 5. Callback Page (`src/modules/auth/pages/OAuthCallbackPage.vue`)

Create page to handle OAuth redirects:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useOAuth } from '@/shared/composables/useOAuth'

const route = useRoute()
const { handleCallback } = useOAuth()

onMounted(() => {
  const provider = route.params.provider as string
  const code = route.query.code as string
  const state = route.query.state as string

  if (provider && code && state) {
    handleCallback(provider, code, state)
  }
})
</script>

<template>
  <div class="flex items-center justify-center min-h-screen">
    <div class="text-center">
      <h2 class="text-xl font-semibold mb-2">Completing sign in...</h2>
      <p class="text-muted-foreground">Please wait</p>
    </div>
  </div>
</template>
```

#### 6. Route Configuration

Add OAuth callback route to `src/router/routes.ts`:

```typescript
{
  path: '/auth/callback/:provider',
  component: () => import('@/modules/auth/pages/OAuthCallbackPage.vue'),
  meta: { layout: 'public' }
}
```

#### 7. Update Login Page

Add OAuth button to existing login page:

```vue
<!-- In LoginPage.vue or similar -->
<template>
  <div class="auth-container">
    <!-- Existing email/password form -->

    <div class="relative my-6">
      <div class="absolute inset-0 flex items-center">
        <span class="w-full border-t" />
      </div>
      <div class="relative flex justify-center text-xs uppercase">
        <span class="bg-background px-2 text-muted-foreground">
          Or continue with
        </span>
      </div>
    </div>

    <OAuthButton />
  </div>
</template>
```

## Database Schema Updates

### SQLite Migration

```sql
-- Add OAuth fields to users table
ALTER TABLE users ADD COLUMN oauth_provider TEXT;
ALTER TABLE users ADD COLUMN oauth_provider_id TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- Add index for OAuth lookup
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_provider_id);

-- Make password nullable for OAuth users
-- (Requires creating new table and migrating data in SQLite)
```

### PostgreSQL Migration

```sql
ALTER TABLE users
  ADD COLUMN oauth_provider VARCHAR(50),
  ADD COLUMN oauth_provider_id VARCHAR(255),
  ADD COLUMN avatar_url TEXT,
  ALTER COLUMN hashed_password DROP NOT NULL;

CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_provider_id);
```

## Environment Variables

### Backend `.env`

```env
# OAuth (Google)
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret_here
GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/auth/callback/google
```

### Frontend `.env`

```env
# OAuth (public client IDs only)
VITE_GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id_here
```

## Security Considerations

1. **CSRF Protection**: Use state parameter to prevent CSRF attacks
2. **Token Storage**: Store OAuth state in localStorage temporarily
3. **HTTPS Required**: OAuth requires HTTPS in production
4. **Rate Limiting**: Apply rate limits to OAuth endpoints
5. **Email Verification**: OAuth emails are pre-verified by providers
6. **Account Linking**: Decide policy for linking OAuth to existing accounts

## Testing Strategy

### Backend Tests

```python
# test_oauth.py
async def test_google_oauth_flow():
    # Test authorization URL generation
    # Test token exchange (mock httpx)
    # Test user info retrieval
    # Test user creation/login

async def test_oauth_csrf_protection():
    # Test state parameter validation

async def test_oauth_rate_limiting():
    # Test rate limits on OAuth endpoints
```

### Frontend Tests

```typescript
// useOAuth.spec.ts
describe('useOAuth', () => {
  it('generates authorization URL', async () => {
    // Test initiateGoogleLogin
  })

  it('handles callback correctly', async () => {
    // Test handleCallback with valid state
  })

  it('detects CSRF attacks', async () => {
    // Test handleCallback with invalid state
  })
})
```

## Implementation Phases

### Phase 1: Backend Core (2-3 hours)
1. Create `oauth.py` service
2. Add OAuth settings to config
3. Update User model
4. Create database migration

### Phase 2: Backend Endpoints (1-2 hours)
1. Add OAuth methods to AuthService
2. Create OAuth endpoints in router
3. Add repository methods
4. Write backend tests

### Phase 3: Frontend Core (2-3 hours)
1. Create `useOAuth` composable
2. Update config
3. Add API client methods
4. Create callback page

### Phase 4: Frontend UI (1-2 hours)
1. Create OAuth button component
2. Update login page
3. Add route configuration
4. Style components

### Phase 5: Testing & Polish (1-2 hours)
1. End-to-end testing
2. Error handling improvements
3. Loading states
4. Documentation

**Total Estimated Time**: 7-12 hours

## Future Enhancements

- Add GitHub OAuth provider
- Support account unlinking
- OAuth token refresh
- Multiple OAuth accounts per user
- Social profile sync

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- Company Hub implementation: `/home/madeyskij/projects/company-hub/app/security/oauth.py`
