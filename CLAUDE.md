# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zbory CHWZ is a Vue 3 application for managing and publicly presenting CHWZ (Chrześcijańska Wspólnota Wolnych Zielonoświątkowców) congregation data. The app uses a multi-tenant architecture with backend API integration for authentication, data management, and admin functionality.

## Commands

### Development
```bash
pnpm dev              # Start development server (default port: 5176)
pnpm build            # Build for production (runs type-check + build-only)
pnpm build-only       # Build without type checking
pnpm preview          # Preview production build
```

### Code Quality
```bash
pnpm type-check       # Run TypeScript compiler check
pnpm lint             # Run ESLint with auto-fix and cache
```

### Testing
```bash
pnpm test             # Run tests in watch mode
pnpm test:ui          # Run tests with Vitest UI
pnpm test:run         # Run tests once (CI mode)
pnpm test:coverage    # Run tests with coverage report
```

### Package Manager
This project uses **pnpm** (version 10.18.3+). Always use `pnpm` instead of `npm` or `yarn`.

### Backend Development

**CRITICAL - Docker Safety Rule:**
- **NEVER run Docker commands if the project directory name starts with underscore (e.g., `_zbory-chwz-dev`)**
- Underscore prefix indicates a development directory on the production server
- Running Docker in such directories can cause conflicts with production services
- If the current working directory starts with `_`, do not execute any `docker` or `docker compose` commands

```bash
docker compose -f backend/docker-compose.dev.yml up    # Start backend in development mode
docker compose -f backend/docker-compose.dev.yml down  # Stop backend
```

**Important:**
- Use `docker compose` (Docker Compose V2 syntax), NOT `docker-compose` (deprecated V1 syntax)
- In development, the backend typically runs in a Docker container via `docker-compose.dev.yml`. This ensures consistent environment and dependencies. The backend is accessible at `http://localhost:8000` (or the port specified in `VITE_API_PROXY_URL`).
- **Auto-reload is enabled** - FastAPI uses WatchFiles to automatically reload when Python files change. No need to restart the container after code changes during development.
- Only restart the container when changing environment variables (`.env`) or dependencies (`requirements.txt`).

### Backend Testing
The backend uses **pytest** for testing with async support via `pytest-asyncio`.

**Running tests:**
```bash
# Option 1: Using Docker (recommended - ensures consistent environment)
docker exec zbory-chwz-app python -m pytest tests/ -v

# Option 2: Using venv (if dependencies are installed)
cd backend
source .venv/bin/activate
python -m pytest tests/ -v

# Run specific test file
docker exec zbory-chwz-app python -m pytest tests/integration/congregations/test_congregations_crud.py -v

# Run with coverage
docker exec zbory-chwz-app python -m pytest tests/ --cov=app --cov-report=html
```

### Backend CLI Commands
The backend includes a CLI tool for administrative tasks located in `backend/cli/`.

**Running CLI commands:**
```bash
# Using Docker (recommended)
docker exec zbory-chwz-app python -m cli <command>

# Using venv (if dependencies are installed)
cd backend
source .venv/bin/activate
python -m cli <command>
```

**User Management Commands:**
```bash
# Create a new user (interactive mode)
python -m cli users create

# Create user with role flag
python -m cli users create --role admin
python -m cli users create --role owner

# Create user non-interactively
python -m cli users create --no-input \
    --email user@example.com \
    --name "User Name" \
    --password "SecurePass123!" \
    --role admin

# List all users
python -m cli users list

# List users with filters
python -m cli users list --admins --detailed

# Delete a user
python -m cli users delete user@example.com

# Toggle admin status
python -m cli users toggle-admin user@example.com

# Set user role (user, premium, admin, owner)
python -m cli users set-role user@example.com --role admin

# Verify user email
python -m cli users verify-email user@example.com --confirm
```

**CLI User Creation Details:**
- **Email**: Required, validated for proper format
- **Name**: Optional, can be left blank to auto-guess from email (extracts part before @, capitalizes, replaces dots/underscores with spaces)
- **Password**: Required, validated for strength, confirmed in interactive mode
- **Role**: Required, must be `admin` or `owner` (interactive menu shows options 1-2 or accepts role name)

## Architecture

### Module-Based Structure

The application follows a **modular architecture** where each feature is self-contained in `src/modules/`. Each module contains:

- `pages/` - Vue page components
- `components/` - Module-specific components
- `store/` - Pinia stores for state management
- `services/` - Business logic layer
- `composables/` - Reusable composition functions
- `types/` - TypeScript type definitions
- `routes.ts` - Module route definitions
- `i18n/` - Module-specific translations

Current modules:
- `auth` - Authentication with WebAuthn/passkeys support
- `user` - User profile management
- `settings` - Application settings
- `admin` - Admin dashboard for managing users and congregations
- `ai` - AI assistance with chat and context management
- `stats` - Statistics and analytics

### Core Directories

- `src/components/` - Shared UI components
  - `ui/` - shadcn-vue components
  - `data-table/` - Table components
  - `layout/` - Layout-related components
- `src/pages/` - Top-level/shared pages (Landing, Privacy, Cookies, Contact, NotFound, Dashboard, Settings)
- `src/layouts/` - Layout wrappers (authenticated, guest, public)
- `src/shared/` - Shared utilities, types, composables, and infrastructure
  - `components/` - Shared components
  - `composables/` - Shared composables
  - `config/` - Shared configuration
  - `i18n/` - i18n infrastructure
  - `services/` - API client, interceptors (auth, error)
  - `store/` - Shared stores (e.g., token refresh)
  - `types/` - Shared TypeScript types
  - `utils/` - Shared utility functions
- `src/router/` - Vue Router configuration
- `src/i18n/` - Application i18n instance (merges module translations)

### State Management Pattern

The app uses a dual state management approach:

**1. Client-Side State (Pinia)**
- **Pinia stores** handle client-side state persistence with localStorage sync
- **Service classes** contain business logic, validation, and calculations

**2. Server State (TanStack Query)**
- **@tanstack/vue-query** manages server state with caching and invalidation
- Used for authentication, AI features, admin operations, congregation data
- Provides automatic background refetching, optimistic updates, and error handling

Example:
```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['congregations'],
  queryFn: fetchCongregations,
  staleTime: 5 * 60 * 1000,
})
```

### Data Persistence

**Server-Side (Backend API)**
- Congregation data and metadata
- User authentication and session tokens
- User profiles and preferences
- Admin data and analytics
- AI model interactions
- Communication via axios with `/api` proxy to backend

### Routing & Layouts

Routes are defined per-module and merged in `src/router/routes.ts`. Each route specifies a layout via `meta.layout`:

```typescript
{
  path: '/congregations',
  component: () => import('@/modules/congregations/pages/CongregationsListPage.vue'),
  meta: { layout: 'authenticated' }
}
```

Available layouts: `authenticated`, `guest`, `public`

**Route Guards:**
- Authentication guard checks user session before accessing protected routes
- Admin guard restricts access to admin-only pages
- Guards are applied per-module and can be composed

### Internationalization (i18n)

The app uses **vue-i18n** with a registry pattern:

1. Each module defines translations in `i18n/locales/` (en, pl)
2. Module translations are exported from `i18n/index.ts`
3. App-level `src/i18n/index.ts` merges all module translations + shared registry
4. Shared i18n utilities are in `src/shared/i18n/`

Locale is persisted in localStorage and synced via `useLocale()` composable.

## Tech Stack & Configuration

### Core Technologies
- **Vue 3.5+** with `<script setup>` and Composition API
- **TypeScript** (strict mode)
- **Pinia** for client-side state management
- **TanStack Query** (@tanstack/vue-query) for server state management
- **Vue Router** for navigation
- **Vite** as build tool

### UI & Styling
- **Tailwind CSS v4** (via `@tailwindcss/vite`)
- **shadcn-vue** components (based on reka-ui)
- **lucide-vue-next** for icons
- **vue-sonner** for toast notifications
- **floating-vue** for tooltips (registered as `v-tooltip` directive)

### Data & Visualization
- **@tanstack/vue-table** for advanced table features
- **@unovis/ts & @unovis/vue** for data visualization and charts

### Form Handling
- **vee-validate** + **@vee-validate/zod** for form validation
- **zod** for schema validation

### Backend & API
- **axios** for HTTP client
- **@simplewebauthn/browser** for WebAuthn/passkeys authentication
- **jwt-decode** for JWT token parsing
- API client with auth and error interceptors (`src/shared/services/`)

### Utilities
- **@vueuse/core** for Vue composition utilities
- **date-fns** for date manipulation
- **markdown-it** for Markdown parsing
- **qrcode** for QR code generation
- **md5** for hashing

### PWA
- **vite-plugin-pwa** for Progressive Web App support
- **workbox-window** for service worker management
- Configuration in `pwa.config.ts`

### Development Tools
- **ESLint** with Vue, TypeScript, and Perfectionist plugins
- **vue-tsc** for TypeScript type checking
- **vite-plugin-vue-devtools** for Vue DevTools

### Testing
- **vitest** for unit testing with happy-dom environment
- **@vitest/ui** for test UI
- **@playwright/test** for end-to-end testing
- Test coverage with v8 provider

## Code Style & Conventions

### ESLint Configuration (eslint.config.ts)

- **No semicolons** (`semi: never`)
- **Single quotes** with escape avoidance
- **Import sorting** (Perfectionist plugin) - alphabetical order with specific groups
- **Self-closing tags** required for all HTML/SVG/Vue components
- **Max attributes per line**: 3 for single-line, 1 for multi-line
- Unused variables starting with `_` are allowed
- **No line breaks before `else`, `catch`, `finally`** - Keep control flow keywords on the same line as closing brace
  - ✅ Use: `} else {`, `} catch (error) {`, `} finally {`
  - ❌ Avoid: Line breaks before these keywords

### TypeScript Conventions

- Use `@/` alias for absolute imports from `src/`
- Create **dedicated union types** instead of inline definitions
- Prefer interfaces for object shapes, types for unions/primitives
- All types are defined in module-specific `types/` directories

### Vue Component Patterns

- Use `<script setup lang="ts">` for all components
- Import order: external packages → internal modules (alphabetical, enforced by ESLint)
- Use composables for reusable logic (e.g., `useAuthStore`, `useLocale`)
- Layouts are rendered via `<RouterView />` in App.vue

### Vue 3.5+ Best Practices

**v-model with defineModel:**
- ✅ Use: `const open = defineModel<boolean>('open', { required: true })`
- ❌ Avoid: `defineProps<{ open: boolean }>()` + `emit('update:open')`
- Benefits: Simpler syntax, automatic reactivity, less boilerplate

**Reactive Destructured Props:**
- Destructured props are reactive in Vue 3.5+ (no need for `toRefs`)
- ✅ Use: `const { item } = defineProps<{ item: ICongregation }>()`
- Props can be used directly in computed/watch without losing reactivity

**Prop Shortcuts:**
- When passing a prop with the same name as the variable
- ✅ Use: `<Dialog :open />` instead of `<Dialog :open="open" />`

**TypeScript Generics:**
- Always provide explicit types for `ref<T>`, `computed<T>`, `reactive<T>`
- ✅ Use: `const count = ref<number>(0)`, `const label = computed<string>(() => ...)`
- ❌ Avoid: `const count = ref(0)` (implicit types)

**Declaration Order in `<script setup>`:**
1. Composables (e.g., `useI18n()`, `useRouter()`)
2. `defineProps()`
3. `defineModel()`
4. `defineEmits()`
5. Computed properties and reactive state
6. Functions and methods

**Routing:**
- Use route helper functions from `routes.ts` instead of hardcoded paths
- ✅ Use: `CongregationRoutePath.Detail(congregationId)`
- ❌ Avoid: `` `/congregations/${congregationId}` ``

## Environment & Configuration

### Environment Variables
- `VITE_PORT` - Development server port (default: 5176)
- `VITE_API_PROXY_URL` - API proxy target (default: http://localhost:8000)

The Vite config proxies `/api` requests to the configured backend URL.

### Node.js Requirements
- Node.js `^20.19.0` or `>=22.12.0` (specified in package.json)

## Key Features (Planned)

### Public Views
1. **Homepage** - Landing page with congregation search
2. **Congregation Search** - Filter and search congregations
3. **Map View** - Google Maps with congregation markers
4. **Public Profiles** - Read-only congregation detail pages

### Congregation Management
5. **Congregation CRUD** - Create, read, update, delete congregation data
6. **Contact Persons** - Manage people associated with congregations
7. **Service Times** - Track multiple service times per congregation
8. **Multi-tenant Access** - Users can manage multiple congregations with different roles

### Authentication & Security
9. **WebAuthn/Passkeys** - Modern passwordless authentication
10. **JWT Tokens** - Secure token-based authentication with auto-refresh
11. **Route Guards** - Protected routes for authenticated and admin users
12. **Session Management** - Automatic token refresh and logout on expiration

### Admin Features
13. **User Management** - Admin dashboard for managing users
14. **Congregation Management** - Admin oversight of all congregations
15. **Analytics** - Statistics and usage analytics

### User Experience
16. **Progressive Web App** - Installable as native app with offline support
17. **Dark Mode** - System-synced theme via settings store
18. **Multi-language** - Polish and English (extensible via i18n registry)
19. **Responsive Design** - Mobile-first design with tablet/desktop optimization
20. **Advanced Tables** - Sortable, filterable tables with TanStack Table

## Important Notes

- **Multi-Tenant Architecture** - Users can be assigned to multiple congregations with different roles
- **Data Persistence** - All data stored server-side via API
- **API Integration** - Backend API proxied at `/api/*` (configured in vite.config.ts)
- **Authentication Required** - Most features require backend authentication (WebAuthn/passkeys)
- **Module Independence** - Modules should be self-contained and reusable
- **Service Layer** - Business logic belongs in service classes, not in stores or components
- **Type Safety** - All data structures have TypeScript interfaces in `types/` directories
- **Guard Composition** - Route guards can be composed for complex authorization logic
- **PWA Offline Support** - Service workers cache assets for offline functionality

## TailwindCSS Best Practices

**Sizing:**
- Prefer `size-{value}` utility class instead of separate `w-{value} h-{value}` when width and height are the same
- ✅ **Correct:** `size-4`, `size-8`, `size-12`
- ❌ **Avoid:** `w-4 h-4`, `w-8 h-8`, `w-12 h-12`

**Button Component Spacing:**
- The Button component already includes `flex` and `gap-2` classes
- Icons inside buttons do **NOT** need `mr-2` or similar margin utilities
- ✅ **Correct:** `<Button><Icon />Label</Button>` (gap handled automatically)
- ❌ **Avoid:** `<Button><Icon class="mr-2" />Label</Button>`

## Responsive Design

**Always consider mobile-first responsive design:**
- Start with mobile styles (base classes)
- Add desktop variants using Tailwind breakpoint prefixes (eg. `sm:`)
- Example: `text-sm sm:text-base lg:text-lg` (small on mobile, base on tablet, large on desktop)
- Consider spacing, typography, layout, and visibility across breakpoints

## Backend Development Notes

- Run `python -m black .` and `python -m mypy .` in backend/ dir before committing Python code.
- Backend uses FastAPI with async/await pattern
- PostgreSQL database with SQLAlchemy ORM
- Redis for session management and caching
- Multi-tenant data isolation at application level
