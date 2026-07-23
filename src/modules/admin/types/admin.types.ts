import type { TDateTime, TUUID } from '@/shared/types/base.type'

export type TUserRole = 'user' | 'admin' | 'premium'

export interface IAdminUser {
  id: TUUID
  name: string
  email: string
  avatarUrl?: string
  isActive: boolean
  isAdmin: boolean
  isOwner: boolean
  isPremium: boolean
  isEmailVerified: boolean
  emailVerifiedAt?: TDateTime | null
  createdAt: TDateTime
  updatedAt: TDateTime
}

export interface IAdminContainer {
  id: TUUID
  name: string
  description?: string | null
  type: string
  color?: string | null
  isPublic: boolean
  authorId?: TUUID | null
  authorName?: string | null
  createdAt: TDateTime
  updatedAt: TDateTime
  itemCount?: number
}

export interface IAdminItem {
  id: TUUID
  name: string
  category: string
  quantity: number
  weight: number
  weightUnit: string
  status: string
  priority: string
  containerId: TUUID
  containerName?: string
  authorId?: TUUID | null
  authorName?: string | null
  createdAt: TDateTime
  updatedAt: TDateTime
}

export type SubscriptionStatus = 'active' | 'canceled' | 'past_due' | 'unpaid' | 'incomplete'
export type PlanTier = 'free' | 'pro' | 'pro_plus'
export type BillingInterval = 'monthly' | 'annual'

export interface IAdminSubscription {
  id: TUUID
  userId: TUUID
  userName: string | null
  userEmail: string | null
  stripeCustomerId: string | null
  stripeSubscriptionId: string | null
  planTier: PlanTier
  billingInterval: BillingInterval | null
  status: SubscriptionStatus
  currentPeriodStart: TDateTime | null
  currentPeriodEnd: TDateTime | null
  cancelAtPeriodEnd: boolean
  isGrandfathered: boolean
  createdAt: TDateTime
  updatedAt: TDateTime
}

export interface IAdminSubscriptionStats {
  totalUsers: number
  totalSubscriptions: number
  activeSubscriptions: number
  canceledSubscriptions: number
  pastDueSubscriptions: number
  freeUsers: number
  proUsers: number
  proPlusUsers: number
  grandfatheredUsers: number
  monthlyRevenue: number
  annualRevenue: number
}

export interface IAdminUpdateSubscriptionRequest {
  planTier?: PlanTier
  status?: SubscriptionStatus
  isGrandfathered?: boolean
  cancelAtPeriodEnd?: boolean
  reason?: string
}
