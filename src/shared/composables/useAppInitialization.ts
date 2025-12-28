/**
 * App initialization composable
 *
 * Handles application-level initialization tasks such as:
 * - Loading user settings (locale, theme)
 * - Setting up global configuration
 * - Pre-fetching critical data
 *
 * This separates initialization logic from App.vue for better
 * code organization, testability, and reusability.
 */

import { computed, watchEffect } from 'vue'
import { useSettingsQuery } from '@/modules/settings/composables/useSettings'
import { useDarkMode } from '@/shared/composables/useDarkMode'
import { useLocale } from '@/shared/i18n'
import type { Settings } from '@/modules/settings/types/settings.type'

export interface AppInitializationState {
  /**
   * Whether the app has finished initializing
   */
  isInitialized: boolean
  /**
   * Initialization error if any
   */
  error: unknown
  /**
   * Settings data
   */
  settings?: Settings
}

/**
 * Initialize application settings and configuration
 *
 * This composable:
 * 1. Loads user settings from the backend
 * 2. Applies locale/language preferences
 * 3. Returns initialization state
 *
 * Usage in App.vue:
 * ```ts
 * const { isInitialized, error } = useAppInitialization()
 * ```
 */
export function useAppInitialization() {
  const { setLocale } = useLocale()
  const { setDark } = useDarkMode()
  const settingsQuery = useSettingsQuery()

  // Watch settings data and apply locale/darkMode when available
  // API has priority - when settings are loaded from API, sync locale and darkMode
  // This ensures LOCALE_STORAGE_KEY is always the source of truth for locale
  watchEffect(() => {
    if (settingsQuery.data.value) {
      // Sync locale via useLocale to ensure LOCALE_STORAGE_KEY is source of truth
      if (settingsQuery.data.value.locale) {
        setLocale(settingsQuery.data.value.locale)
      }
      // Sync darkMode via useDarkMode
      if (settingsQuery.data.value.darkMode !== undefined) {
        setDark(settingsQuery.data.value.darkMode)
      }
    }
  })

  // Computed: App is initialized when settings query has finished (success or error)
  // Note: settingsQuery.isPending is already a Ref from vue-query
  const isInitialized = computed(() => !settingsQuery.isPending.value)

  return {
    isInitialized,
    error: settingsQuery.error,
    settings: settingsQuery.data,
    // Expose query state for advanced use cases
    isLoading: settingsQuery.isPending,
    isError: settingsQuery.isError,
  }
}

