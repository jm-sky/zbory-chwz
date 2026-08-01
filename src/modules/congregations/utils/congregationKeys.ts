import { toValue, type MaybeRefOrGetter } from 'vue'

export const congregationKeys = {
  all: ['congregations'] as const,
  list: (isAuthenticated: MaybeRefOrGetter<boolean>) =>
    [...congregationKeys.all, 'detailed', toValue(isAuthenticated)] as const,
  detail: (id: MaybeRefOrGetter<string>) =>
    [...congregationKeys.all, 'detail', toValue(id)] as const,
}
