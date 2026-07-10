// Application i18n configuration
// This file merges registry messages with module-specific messages
// and creates the i18n instance for your application.
//
// IMPORTANT: This file uses createI18nInstance() from @/shared/i18n
// instead of duplicating the i18n configuration logic.

// Import module messages
import { adminEn, adminPl, adminRu } from '@/modules/admin/i18n'
import { authEn, authPl, authRu } from '@/modules/auth/i18n'
import { congregationsEn, congregationsPl } from '@/modules/congregations/i18n'
import { groupsEn, groupsPl } from '@/modules/groups/i18n'
import { settingsEn, settingsPl, settingsRu } from '@/modules/settings/i18n'
import { userEn, userPl, userRu } from '@/modules/user/i18n'
import { createI18nInstance } from '@/shared/i18n'
// Import registry base messages (validation, errors, common)
import registryEn from '@/shared/i18n/locales/en'
import registryPl from '@/shared/i18n/locales/pl'
import registryRu from '@/shared/i18n/locales/ru'

// Import app-specific messages (if you have any custom translations)
// import appEn from './locales/en'
// import appPl from './locales/pl'

// Merge all messages together
const en = {
  ...registryEn,
  ...adminEn,
  ...authEn,
  ...congregationsEn,
  ...groupsEn,
  ...settingsEn,
  ...userEn,
}
const pl = {
  ...registryPl,
  ...adminPl,
  ...authPl,
  ...congregationsPl,
  ...groupsPl,
  ...settingsPl,
  ...userPl,
}
const ru = {
  ...registryRu,
  ...adminRu,
  ...authRu,
  ...settingsRu,
  ...userRu,
}

// If you have app-specific messages, merge them here:
// const en = { ...registryEn, ...appEn }
// const pl = { ...registryPl, ...appPl }

// Export merged type for type safety
export type Messages = typeof en

/**
 * Application i18n instance with all merged messages
 * Uses createI18nInstance from registry which handles locale detection,
 * localStorage persistence, and browser language detection
 */
export const i18n = createI18nInstance({
  messages: {
    en,
    pl,
    ru,
  },
})
