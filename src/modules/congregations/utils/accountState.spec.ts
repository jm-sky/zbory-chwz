import { describe, expect, it } from 'vitest'
import type { IAccountState } from '../types/church.types'
import { accountBadgeVariant, canInviteAccount, isResendInvite } from './accountState'

function account(overrides: Partial<IAccountState> = {}): IAccountState {
  return {
    userId: 'u1',
    status: 'invited',
    invitedAt: '2026-07-01T00:00:00.000Z',
    invitationExpiresAt: '2026-07-08T00:00:00.000Z',
    ...overrides,
  }
}

describe('canInviteAccount', () => {
  it('is hidden without a linked account', () => {
    expect(canInviteAccount(null, true)).toBe(false)
  })

  it('is hidden without the manage permission, even with an invitable account', () => {
    expect(canInviteAccount(account({ status: 'none' }), false)).toBe(false)
  })

  it('is hidden once the account is active', () => {
    expect(canInviteAccount(account({ status: 'active' }), true)).toBe(false)
  })

  it('is visible for none/invited/expired accounts when the caller can manage people', () => {
    expect(canInviteAccount(account({ status: 'none' }), true)).toBe(true)
    expect(canInviteAccount(account({ status: 'invited' }), true)).toBe(true)
    expect(canInviteAccount(account({ status: 'expired' }), true)).toBe(true)
  })
})

describe('isResendInvite', () => {
  it('is false with no account or a fresh (never invited) account', () => {
    expect(isResendInvite(null)).toBe(false)
    expect(isResendInvite(account({ status: 'none' }))).toBe(false)
  })

  it('is true for invited or expired accounts', () => {
    expect(isResendInvite(account({ status: 'invited' }))).toBe(true)
    expect(isResendInvite(account({ status: 'expired' }))).toBe(true)
  })
})

describe('accountBadgeVariant', () => {
  it('maps each status to a distinct badge variant', () => {
    expect(accountBadgeVariant('active')).toBe('success')
    expect(accountBadgeVariant('invited')).toBe('secondary')
    expect(accountBadgeVariant('expired')).toBe('destructive')
    expect(accountBadgeVariant('none')).toBe('outline')
  })
})
