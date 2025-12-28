/**
 * Tenant/Congregation types for admin
 */

export interface IAdminTenant {
  id: string
  name: string
  description?: string
  status?: string
  createdAt: string
}

export interface IAdminTenantMembership {
  tenant_id: string
  user_id: string
  user_name?: string
  user_email?: string
  role: string
  createdAt: string
}

export interface ICreateTenantRequest {
  name: string
  description?: string
  status?: string
}

export interface IUpdateTenantRequest {
  name?: string
  description?: string
  status?: string
}

export interface ICreateTenantMembershipRequest {
  user_id: string
  role: string
}

export interface IUpdateTenantMembershipRequest {
  role: string
}

export interface IAddress {
  id: string
  tenant_id: string
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country: string
  status: string
  created_at: string
  updated_at: string
}

export interface IAddressUpdateRequest {
  street?: string | null
  city?: string | null
  postal_code?: string | null
  province?: string | null
  country?: string | null
  status?: string | null
}

export interface IAddressCreateRequest {
  street?: string | null
  city: string
  postal_code?: string | null
  province?: string | null
  country?: string
  status?: string
}
