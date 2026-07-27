import type { MaybeRefOrGetter } from 'vue'

export const governanceKeys = {
  all: ['governance'] as const,
  roleAssignments: (scopeType: MaybeRefOrGetter<string>, scopeId: MaybeRefOrGetter<string>) =>
    [...governanceKeys.all, 'role-assignments', scopeType, scopeId] as const,
}
