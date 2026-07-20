import type { MaybeRefOrGetter } from 'vue'

export const congregationKeys = {
  all: ['congregations'] as const,
  list: (isAuthenticated: MaybeRefOrGetter<boolean>) => [...congregationKeys.all, 'detailed', isAuthenticated] as const,
  detail: (id: MaybeRefOrGetter<string>) => [...congregationKeys.all, 'detail', id] as const,
}
