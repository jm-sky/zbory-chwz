# Church Addresses Implementation Plan

## Overview

This document outlines the plan for implementing church address management functionality, including database migrations, backend API endpoints, and frontend management views.

## Architecture

### Database Schema

**Table: `addresses`**
- `id` (UUID, PRIMARY KEY) - Unique identifier
- `tenant_id` (UUID, FOREIGN KEY → `tenants.id`) - Reference to congregation/church
- `type` (VARCHAR(50)) - Address type: `main`, `mailing`, `service`, `other`
- `street` (VARCHAR(255)) - Street address
- `city` (VARCHAR(100)) - City name
- `postal_code` (VARCHAR(20)) - Postal/ZIP code
- `province` (VARCHAR(100), NULLABLE) - State/Province/Region (optional)
- `country` (VARCHAR(100)) - Country name (default: "Poland")
- `latitude` (DECIMAL(10, 8), NULLABLE) - GPS latitude for mapping
- `longitude` (DECIMAL(11, 8), NULLABLE) - GPS longitude for mapping
- `google_maps_url` (TEXT, NULLABLE) - Google Maps profile/place URL
- `status` (VARCHAR(50)) - Record status: `draft`, `need_verification`, `published`, `archived` (default: `draft`)
- `is_primary` (BOOLEAN) - Whether this is the primary address (default: false)
- `notes` (TEXT, NULLABLE) - Additional notes about the address
- `created_at` (TIMESTAMP WITH TIME ZONE) - Creation timestamp
- `updated_at` (TIMESTAMP WITH TIME ZONE) - Last update timestamp

**Table: `address_versions`** (Versioning/Audit Trail)
- `id` (UUID, PRIMARY KEY) - Unique identifier for version record
- `address_id` (UUID, FOREIGN KEY → `addresses.id`) - Reference to original address
- `version_number` (INTEGER) - Sequential version number (1, 2, 3, ...)
- `action` (VARCHAR(20)) - Action that created this version: `create`, `update`, `delete`
- `tenant_id` (UUID) - Snapshot of tenant_id at time of version
- `type` (VARCHAR(50)) - Snapshot of address type
- `street` (VARCHAR(255)) - Snapshot of street
- `city` (VARCHAR(100)) - Snapshot of city
- `postal_code` (VARCHAR(20)) - Snapshot of postal_code
- `province` (VARCHAR(100), NULLABLE) - Snapshot of province
- `country` (VARCHAR(100)) - Snapshot of country
- `latitude` (DECIMAL(10, 8), NULLABLE) - Snapshot of latitude
- `longitude` (DECIMAL(11, 8), NULLABLE) - Snapshot of longitude
- `google_maps_url` (TEXT, NULLABLE) - Snapshot of Google Maps URL
- `status` (VARCHAR(50)) - Snapshot of status
- `is_primary` (BOOLEAN) - Snapshot of is_primary
- `notes` (TEXT, NULLABLE) - Snapshot of notes
- `created_by` (UUID, FOREIGN KEY → `users.id`, NULLABLE) - User who made the change
- `created_at` (TIMESTAMP WITH TIME ZONE) - When this version was created

**Constraints:**
- Only one primary address per tenant (`is_primary = true`)
- `type` must be one of: `main`, `mailing`, `service`, `other`
- `status` must be one of: `draft`, `need_verification`, `published`, `archived`
- `country` defaults to "Poland" if not specified
- `tenant_id` is required (addresses belong to congregations)
- `version_number` must be unique per `address_id` (enforced by application logic or unique index)

**Indexes:**
- `idx_addresses_tenant_id` on `addresses(tenant_id)` (for fast tenant lookups)
- `idx_addresses_type` on `addresses(type)` (for filtering by type)
- `idx_addresses_status` on `addresses(status)` (for filtering by status)
- `idx_addresses_is_primary` on `addresses(is_primary)` (for finding primary addresses)
- `idx_address_versions_address_id` on `address_versions(address_id)` (for version lookups)
- `idx_address_versions_created_at` on `address_versions(created_at)` (for chronological queries)
- Unique constraint: `(tenant_id, is_primary)` where `is_primary = true` on `addresses` (ensures single primary address)

### Backend Module Structure

**Module: `app/modules/addresses/`**

```
addresses/
├── __init__.py
├── db_models.py          # SQLAlchemy models
├── repositories.py       # Data access layer
├── schemas.py            # Pydantic schemas for API
├── router.py             # FastAPI endpoints
├── service.py            # Business logic (optional, if needed)
└── exceptions.py         # Custom exceptions (optional)
```

### Frontend Module Structure

**Module: `src/modules/addresses/`**

```
addresses/
├── components/
│   ├── AddressForm.vue           # Form for create/edit
│   ├── AddressList.vue           # List view component
│   ├── AddressCard.vue           # Card display component
│   └── AddressMap.vue             # Map visualization (optional)
├── pages/
│   ├── AddressesListPage.vue     # Main list page
│   └── AddressEditPage.vue        # Create/edit page
├── services/
│   └── addressApiService.ts      # API client
├── types/
│   └── address.types.ts           # TypeScript types
├── routes.ts                      # Route definitions
└── i18n/
    ├── index.ts
    └── locales/
        ├── en.ts
        └── pl.ts
```

## Implementation Steps

### Phase 1: Database Migration

**File: `backend/migrations/034_add_addresses_table.py`**

1. Create migration script following existing pattern
2. Create `addresses` table with all columns
3. Add indexes and constraints
4. Add foreign key constraint to `tenants` table
5. Add unique constraint for primary address per tenant
6. Include both upgrade and downgrade functions

**SQL Migration: `backend/migrations/034_add_addresses_table.sql`**

For manual application if needed.

### Phase 2: Backend Models & Schemas

**File: `backend/app/modules/addresses/db_models.py`**

- `AddressDB` model inheriting from `Base`
- `AddressVersionDB` model for versioning table
- All columns mapped with proper types
- Relationships to `TenantDB` (many-to-one)
- Relationships to `UserDB` for `created_by` in versions (optional)

**File: `backend/app/modules/addresses/schemas.py`**

- `AddressCreateRequest` - For creating addresses
- `AddressUpdateRequest` - For updating addresses (partial)
- `AddressResponse` - For API responses
- `AddressListResponse` - For list endpoints
- `AddressVersionResponse` - For version history responses
- `AddressVersionListResponse` - For version list endpoints
- Validation rules:
  - `type` enum validation (`main`, `mailing`, `service`, `other`)
  - `status` enum validation (`draft`, `need_verification`, `published`, `archived`)
  - `street`, `city`, `postal_code`, `country` required
  - `latitude`/`longitude` range validation (-90 to 90, -180 to 180)
  - `postal_code` format validation (optional, country-specific)
  - `google_maps_url` URL format validation (optional)

### Phase 3: Backend Repository

**File: `backend/app/modules/addresses/repositories.py`**

- `AddressRepository` class
- Methods:
  - `create_address()` - Create new address (creates version with action='create')
  - `get_address()` - Get single address by ID
  - `list_addresses_for_tenant()` - List all addresses for a tenant
  - `update_address()` - Update address (creates version before update)
  - `delete_address()` - Delete address (creates version with action='delete' before deletion)
  - `set_primary_address()` - Set address as primary (unset others)
  - `get_primary_address()` - Get primary address for tenant
  - `get_address_versions()` - Get version history for an address
  - `get_address_version()` - Get specific version by version_number
  - `restore_address_version()` - Restore address from a specific version
- Handle primary address constraint (only one primary per tenant)
- **Versioning Logic:**
  - Before each `update_address()`: Create version record with current state, increment version_number
  - Before each `delete_address()`: Create version record with current state, mark action='delete'
  - On `create_address()`: Create version record with action='create', version_number=1
  - Track `created_by` user ID for audit trail

### Phase 4: Backend Router

**File: `backend/app/modules/addresses/router.py`**

**Endpoints:**

1. **GET `/api/addresses`** - List all addresses for current user's tenants
   - Query params: `tenant_id` (optional filter), `status` (optional filter)
   - Returns: `AddressListResponse`
   - Auth: Required (`CurrentUser`)

2. **GET `/api/tenants/{tenant_id}/addresses`** - List addresses for specific tenant
   - Query params: `status` (optional filter)
   - Returns: `AddressListResponse`
   - Auth: Required, tenant membership check

3. **GET `/api/addresses/{address_id}`** - Get single address
   - Returns: `AddressResponse`
   - Auth: Required, ownership check

4. **POST `/api/tenants/{tenant_id}/addresses`** - Create new address
   - Body: `AddressCreateRequest`
   - Returns: `AddressResponse`
   - Auth: Required, tenant membership check
   - Status: 201 Created
   - Creates version record with action='create'

5. **PUT `/api/addresses/{address_id}`** - Update address
   - Body: `AddressUpdateRequest`
   - Returns: `AddressResponse`
   - Auth: Required, ownership check
   - Creates version record before update

6. **PATCH `/api/addresses/{address_id}/primary`** - Set as primary address
   - Returns: `AddressResponse`
   - Auth: Required, ownership check
   - Automatically unsets other primary addresses for the tenant
   - Creates version record if status changes

7. **PATCH `/api/addresses/{address_id}/status`** - Update address status
   - Body: `{ "status": "draft" | "need_verification" | "published" | "archived" }`
   - Returns: `AddressResponse`
   - Auth: Required, ownership check (admin can change any status)
   - Creates version record before status change

8. **DELETE `/api/addresses/{address_id}`** - Delete address
   - Returns: 204 No Content
   - Auth: Required, ownership check
   - Creates version record with action='delete' before deletion
   - Prevent deletion if it's the only address for tenant (optional validation)

9. **GET `/api/addresses/{address_id}/versions`** - Get version history for address
   - Returns: `AddressVersionListResponse`
   - Auth: Required, ownership check

10. **GET `/api/addresses/{address_id}/versions/{version_number}`** - Get specific version
    - Returns: `AddressVersionResponse`
    - Auth: Required, ownership check

11. **POST `/api/addresses/{address_id}/versions/{version_number}/restore`** - Restore from version
    - Returns: `AddressResponse`
    - Auth: Required, ownership check
    - Creates new version before restore

**Authorization:**
- Users can only manage addresses for tenants they belong to
- Check tenant membership before allowing operations
- Admin users can manage all addresses (optional enhancement)

### Phase 5: Frontend Types

**File: `src/modules/addresses/types/address.types.ts`**

```typescript
export type AddressType = 'main' | 'mailing' | 'service' | 'other'
export type AddressStatus = 'draft' | 'need_verification' | 'published' | 'archived'

export interface IAddress {
  id: string
  tenantId: string
  type: AddressType
  street: string
  city: string
  postalCode: string
  province?: string
  country: string
  latitude?: number
  longitude?: number
  googleMapsUrl?: string
  status: AddressStatus
  isPrimary: boolean
  notes?: string
  createdAt: string
  updatedAt: string
}

export interface IAddressCreate {
  tenantId: string
  type: AddressType
  street: string
  city: string
  postalCode: string
  province?: string
  country: string
  latitude?: number
  longitude?: number
  googleMapsUrl?: string
  status?: AddressStatus // Defaults to 'draft'
  isPrimary?: boolean
  notes?: string
}

export interface IAddressUpdate extends Partial<IAddressCreate> {
  // Partial update
}

export interface IAddressVersion {
  id: string
  addressId: string
  versionNumber: number
  action: 'create' | 'update' | 'delete'
  tenantId: string
  type: AddressType
  street: string
  city: string
  postalCode: string
  province?: string
  country: string
  latitude?: number
  longitude?: number
  googleMapsUrl?: string
  status: AddressStatus
  isPrimary: boolean
  notes?: string
  createdBy?: string
  createdAt: string
}
```

### Phase 6: Frontend API Service

**File: `src/modules/addresses/services/addressApiService.ts`**

- Use `apiClient` from `@/shared/services/apiClient`
- Methods:
  - `listAddresses(tenantId?: string, status?: AddressStatus)`
  - `getAddress(addressId: string)`
  - `createAddress(tenantId: string, data: IAddressCreate)`
  - `updateAddress(addressId: string, data: IAddressUpdate)`
  - `updateAddressStatus(addressId: string, status: AddressStatus)`
  - `setPrimaryAddress(addressId: string)`
  - `deleteAddress(addressId: string)`
  - `getAddressVersions(addressId: string)`
  - `getAddressVersion(addressId: string, versionNumber: number)`
  - `restoreAddressVersion(addressId: string, versionNumber: number)`

### Phase 7: Frontend Components

**File: `src/modules/addresses/components/AddressForm.vue`**

- Form for creating/editing addresses
- Fields:
  - Tenant selector (if creating, or display if editing)
  - Type (dropdown: main, mailing, service, other)
  - Street (text input)
  - City (text input)
  - Postal code (text input)
  - Province (optional text input)
  - Country (text input with default "Poland")
  - Latitude/Longitude (optional number inputs)
  - Google Maps URL (optional URL input with validation)
  - Status (dropdown: draft, need_verification, published, archived)
  - Is Primary (checkbox)
  - Notes (textarea)
- Validation using vee-validate + zod
- Submit handler
- Status field disabled for non-admin users (or show read-only)

**File: `src/modules/addresses/components/AddressList.vue`**

- Display list of addresses
- Filter by tenant (if multiple)
- Filter by type
- Filter by status (draft, need_verification, published, archived)
- Show primary address indicator
- Show status badge with color coding
- Actions: Edit, Delete, Set Primary, Change Status
- Empty state

**File: `src/modules/addresses/components/AddressCard.vue`**

- Card component for displaying single address
- Show all address fields including Google Maps URL (as link)
- Visual indicator for primary address
- Status badge
- Actions: Edit, Delete, Set Primary, Change Status
- Link to version history

### Phase 8: Frontend Pages

**File: `src/modules/addresses/pages/AddressesListPage.vue`**

- Main page for managing addresses
- Uses `AddressList` component
- Add new address button
- Filtering and search
- Layout: authenticated

**File: `src/modules/addresses/pages/AddressEditPage.vue`**

- Create/edit address page
- Uses `AddressForm` component
- Route params: `tenantId` (for create), `addressId` (for edit)
- Layout: authenticated

**File: `src/modules/addresses/pages/AddressVersionsPage.vue`**

- Version history page for an address
- Display list of versions with timestamps and actions
- Show version details
- Restore button for each version
- Route params: `addressId`
- Layout: authenticated

### Phase 9: Routes & Navigation

**File: `src/modules/addresses/routes.ts`**

```typescript
export const AddressRoutes = {
  List: () => '/addresses',
  Create: (tenantId: string) => `/tenants/${tenantId}/addresses/new`,
  Edit: (addressId: string) => `/addresses/${addressId}/edit`,
  Versions: (addressId: string) => `/addresses/${addressId}/versions`,
}
```

- Register routes in main router
- Add navigation links in tenant/congregation detail pages

### Phase 10: Internationalization

**Files: `src/modules/addresses/i18n/locales/{en,pl}.ts`**

- Translation keys:
  - `addresses.list.title`
  - `addresses.list.empty`
  - `addresses.form.title.create`
  - `addresses.form.title.edit`
  - `addresses.form.fields.*`
  - `addresses.types.*`
  - `addresses.status.*` (draft, need_verification, published, archived)
  - `addresses.actions.*`
  - `addresses.messages.*`
  - `addresses.versions.*`

### Phase 11: Integration with Tenants

- Add address management section to tenant detail pages
- Show primary address in tenant list/cards
- Link to address management from tenant pages

## Status Workflow

### Status States

1. **`draft`** - Initial state, address being created/edited
   - Can transition to: `need_verification`, `archived`
   - Users can edit freely

2. **`need_verification`** - Address submitted for review/verification
   - Can transition to: `published`, `draft` (if rejected), `archived`
   - Typically set by user when ready for publication
   - Admin can verify and publish

3. **`published`** - Address verified and publicly visible
   - Can transition to: `archived`, `need_verification` (if needs re-verification)
   - Publicly visible (if public API exists)
   - Changes may require re-verification

4. **`archived`** - Address no longer active/used
   - Can transition to: `draft` (if reactivated)
   - Hidden from public views
   - Preserved for historical records

### Status Transition Rules

**User Permissions:**
- Regular users: Can set `draft` → `need_verification`
- Regular users: Cannot directly set `published` (admin only)
- Regular users: Can archive their own addresses

**Admin Permissions:**
- Admins: Can set any status
- Admins: Can publish addresses (`need_verification` → `published`)
- Admins: Can reject addresses (`need_verification` → `draft`)

**Business Logic:**
- Status changes create version records
- Only `published` addresses may be shown in public APIs (if implemented)
- Filtering by status available in list endpoints

## Versioning Implementation Details

### Version Creation Logic

**On Create:**
1. Create address record
2. Create version record with:
   - `action = 'create'`
   - `version_number = 1`
   - All address fields copied
   - `created_by = current_user.id`

**On Update:**
1. Get current address state
2. Create version record with current state:
   - `action = 'update'`
   - `version_number = max(version_number) + 1` for this address_id
   - All current address fields copied
   - `created_by = current_user.id`
3. Update address record with new values

**On Delete:**
1. Get current address state
2. Create version record with current state:
   - `action = 'delete'`
   - `version_number = max(version_number) + 1` for this address_id
   - All current address fields copied
   - `created_by = current_user.id`
3. Delete address record

**On Status Change:**
- Treated as update, creates version record

**On Restore:**
1. Get version record to restore
2. Create version record with current state (before restore):
   - `action = 'update'`
   - `version_number = max(version_number) + 1`
3. Restore address fields from selected version

### Version Number Management

- Version numbers are sequential per address (1, 2, 3, ...)
- Use `MAX(version_number)` query to get next version number
- Consider using database sequence or application-level counter
- Version numbers are immutable once created

### Performance Considerations

- Version table can grow large over time
- Consider archiving old versions (>1 year) to separate table
- Index on `(address_id, version_number)` for fast lookups
- Index on `created_at` for chronological queries

## Database Migration Details

### Migration File Structure

```python
"""Migration: Add addresses and address_versions tables.

This migration creates:
1. The addresses table for storing church/congregation addresses.
   Addresses support multiple types (main, mailing, service, other), 
   statuses (draft, need_verification, published, archived), and can be 
   marked as primary. Only one primary address is allowed per tenant.

2. The address_versions table for versioning/audit trail.
   Stores historical versions of addresses before each update/delete.

Usage:
    python migrations/034_add_addresses_table.py upgrade
    python migrations/034_add_addresses_table.py downgrade
```

# Follow existing migration pattern
# - Check if tables exist
# - Create addresses table with all columns (including status, google_maps_url)
# - Create address_versions table with all snapshot columns
# - Add indexes for both tables
# - Add constraints (CHECK for status, type enums)
# - Add foreign keys
# - Handle downgrade (drop tables in reverse order)

### Key Constraints

1. **Primary Address Constraint:**
   - Use a unique partial index: `CREATE UNIQUE INDEX idx_addresses_primary_per_tenant ON addresses(tenant_id) WHERE is_primary = true`
   - Or use a trigger/application logic to ensure only one primary

2. **Foreign Keys:**
   - `FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE` on `addresses`
   - `FOREIGN KEY (address_id) REFERENCES addresses(id) ON DELETE CASCADE` on `address_versions`
   - `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL` on `address_versions` (optional)

3. **Type Validation:**
   - Use CHECK constraint: `CHECK (type IN ('main', 'mailing', 'service', 'other'))` on `addresses`

4. **Status Validation:**
   - Use CHECK constraint: `CHECK (status IN ('draft', 'need_verification', 'published', 'archived'))` on `addresses`
   - Same constraint on `address_versions` table

5. **Version Number:**
   - Application logic ensures sequential version numbers per address
   - Consider unique index: `CREATE UNIQUE INDEX idx_address_versions_unique ON address_versions(address_id, version_number)`

## API Endpoint Details

### Request/Response Examples

**Create Address:**
```json
POST /api/tenants/{tenant_id}/addresses
{
  "type": "main",
  "street": "ul. Example 123",
  "city": "Warsaw",
  "postalCode": "00-001",
  "province": "Mazowieckie",
  "country": "Poland",
  "googleMapsUrl": "https://maps.google.com/...",
  "status": "draft",
  "isPrimary": true
}
```

**Response:**
```json
{
  "id": "uuid",
  "tenantId": "uuid",
  "type": "main",
  "street": "ul. Example 123",
  "city": "Warsaw",
  "postalCode": "00-001",
  "province": "Mazowieckie",
  "country": "Poland",
  "googleMapsUrl": "https://maps.google.com/...",
  "status": "draft",
  "isPrimary": true,
  "createdAt": "2025-01-27T10:00:00Z",
  "updatedAt": "2025-01-27T10:00:00Z"
}
```

**Update Status:**
```json
PATCH /api/addresses/{address_id}/status
{
  "status": "published"
}
```

**Get Versions:**
```json
GET /api/addresses/{address_id}/versions

Response:
{
  "versions": [
    {
      "id": "uuid",
      "addressId": "uuid",
      "versionNumber": 2,
      "action": "update",
      "street": "ul. Old Street 456",
      "city": "Warsaw",
      "status": "draft",
      "createdBy": "user-uuid",
      "createdAt": "2025-01-26T10:00:00Z"
    },
    {
      "id": "uuid",
      "addressId": "uuid",
      "versionNumber": 1,
      "action": "create",
      "street": "ul. Example 123",
      "city": "Warsaw",
      "status": "draft",
      "createdBy": "user-uuid",
      "createdAt": "2025-01-25T10:00:00Z"
    }
  ]
}
```

## Testing Considerations

### Backend Tests

- Unit tests for repository methods
- Integration tests for API endpoints
- Test primary address constraint
- Test tenant membership authorization
- Test address deletion
- **Versioning tests:**
  - Test version creation on create/update/delete
  - Test version number sequencing
  - Test version restore functionality
  - Test version history retrieval
- **Status tests:**
  - Test status transitions
  - Test status filtering
  - Test admin status change permissions

### Frontend Tests

- Component tests for form validation
- Component tests for list display
- E2E tests for CRUD operations

## Future Enhancements

1. **Geocoding Integration:**
   - Auto-populate latitude/longitude from address
   - Use Google Maps Geocoding API or similar

2. **Map Visualization:**
   - Display addresses on map
   - Show all addresses for a tenant on map

3. **Address Validation:**
   - Integrate with postal service APIs
   - Validate postal codes per country

4. **Bulk Operations:**
   - Import addresses from CSV
   - Export addresses

5. **Address History:** ✅ **Implemented via versioning**
   - Track address changes over time
   - Show address history for tenants
   - Restore previous versions

6. **Status Workflow:**
   - Implement status transition rules (e.g., draft → need_verification → published)
   - Add status change notifications
   - Add admin approval workflow for published status

## Dependencies

### Backend
- No new dependencies required
- Uses existing SQLAlchemy, FastAPI, Pydantic

### Frontend
- No new dependencies required
- Uses existing Vue 3, TanStack Query, vee-validate, zod

## Timeline Estimate

- Phase 1 (Migration): 2-3 hours (includes versioning table)
- Phase 2 (Models & Schemas): 2-3 hours (includes version models)
- Phase 3 (Repository): 4-5 hours (includes versioning logic)
- Phase 4 (Router): 3-4 hours (includes version endpoints)
- Phase 5 (Frontend Types): 1 hour (includes version types)
- Phase 6 (API Service): 1-2 hours (includes version methods)
- Phase 7 (Components): 5-7 hours (includes status UI, version components)
- Phase 8 (Pages): 3-4 hours (includes versions page)
- Phase 9 (Routes): 1 hour
- Phase 10 (i18n): 2-3 hours (includes status translations)
- Phase 11 (Integration): 2-3 hours

**Total Estimate: 26-35 hours**

## Notes

- Addresses are tied to tenants (congregations), not users directly
- Users manage addresses through their tenant memberships
- **Versioning:** All changes are tracked automatically before updates/deletes
- **Status Management:** Addresses have workflow states (draft → need_verification → published)
- **Google Maps Integration:** URLs stored for linking to Google Maps profiles/places
- Consider adding address validation service in the future
- Map integration can be added as a separate feature
- Consider adding address search/filtering capabilities
- Version history provides full audit trail for compliance
- Status field allows for moderation workflow (need_verification → published)
