import type { AccountStatus, IAccountState } from '../types/church.types'

type AccountBadgeVariant = 'success' | 'secondary' | 'destructive' | 'outline'

const ACCOUNT_BADGE_VARIANT: Record<AccountStatus, AccountBadgeVariant> = {
  active: 'success',
  invited: 'secondary',
  expired: 'destructive',
  none: 'outline',
}

export function accountBadgeVariant(status: AccountStatus): AccountBadgeVariant {
  return ACCOUNT_BADGE_VARIANT[status]
}

/**
 * Whether the "send/resend invitation" action should be offered for this assignment.
 * The API is the real authority (assert_can_assign_service_type) — this only controls
 * whether the button renders, per §10 "guard jest wyłącznie UX-owy".
 */
export function canInviteAccount(account: IAccountState | null, hasManagePermission: boolean): boolean {
  return !!account && account.status !== 'active' && hasManagePermission
}

export function isResendInvite(account: IAccountState | null): boolean {
  return account?.status === 'invited' || account?.status === 'expired'
}
