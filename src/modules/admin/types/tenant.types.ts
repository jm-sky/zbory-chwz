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
