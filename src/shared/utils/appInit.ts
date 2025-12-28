/**
 * App Initialization Utilities
 *
 * Helper functions for application initialization tasks such as:
 * - Setting HTML lang attribute based on i18n locale
 * - Initializing stores with async data loading
 * - Other initialization utilities
 */

import type { I18n } from 'vue-i18n'

/**
 * Get current locale from i18n instance
 *
 * @param i18n - Vue i18n instance
 * @returns Current locale string
 */
function getCurrentLocale(i18n: I18n): string {
  return typeof i18n.global.locale === 'string' ? i18n.global.locale : i18n.global.locale.value
}

/**
 * Set HTML lang attribute based on current i18n locale
 * This should be called during app initialization to ensure the HTML element
 * has the correct lang attribute for accessibility and SEO
 *
 * @param i18n - Vue i18n instance
 */
export function setHtmlLangAttribute(i18n: I18n): void {
  if (typeof document === 'undefined') {
    return
  }

  const currentLocale = getCurrentLocale(i18n)
  document.documentElement.setAttribute('lang', currentLocale)
}

/**
 * H5 FIX: Initialize stores asynchronously to avoid blocking main thread
 * This should be called during app initialization to load data from localStorage
 * without blocking the initial render
 */
export async function initializeStores(): Promise<void> {
  // No stores to initialize yet
  // Add store initialization here when needed
}

