// shared/config/config.ts

// Supported locales type (defined here to avoid cyclic dependencies)
export type SupportedLocale = 'en' | 'pl' | 'ru'
export type TGearWeightUnit = 'g' | 'kg' | 'oz' | 'lb'

export interface IAiModelPricing {
  input: number // per 1M tokens
  output: number // per 1M tokens
}

export interface IAiModel {
  id: string
  name: string
  provider: string
  context_window: number
  pricing: IAiModelPricing
  recommended_for: string[]
  description?: string
  available?: boolean
}

export const config = {
  app: {
    id: import.meta.env.VITE_APP_ID ?? 'zbory-chwz',
    name: import.meta.env.VITE_APP_NAME ?? 'Zbory CHWZ',
    description: import.meta.env.VITE_APP_DESCRIPTION ?? 'Aplikacja do zarządzania i publicznej prezentacji zborów CHWZ.',
  },
  i18n: {
    defaultLocale: (import.meta.env.VITE_DEFAULT_LOCALE ?? 'en') as SupportedLocale,
    fallbackLocale: (import.meta.env.VITE_FALLBACK_LOCALE ?? 'en') as SupportedLocale,
  },
  contact: {
    companyName: import.meta.env.VITE_COMPANY_NAME ?? 'DEV Made IT',
    companyWebsite: import.meta.env.VITE_COMPANY_WEBSITE ?? 'https://dev-made.it',
    email: import.meta.env.VITE_CONTACT_EMAIL ?? 'contact@dev-made.it',
    officialCompanyName: import.meta.env.VITE_OFFICIAL_COMPANY_NAME ?? 'SAVA GROUP sp. z o.o.',
    officialCompanyWebsite: import.meta.env.VITE_OFFICIAL_COMPANY_WEBSITE ?? 'https://sava-group.pl',
  },
  backend: {
    enabled: import.meta.env.VITE_ENABLE_BACKEND === 'true',
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
  },
  recaptcha: {
    siteKey: import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY ?? '',
    enabled: !!import.meta.env.VITE_GOOGLE_RECAPTCHA_SITE_KEY,
  },
  oauth: {
    google: {
      clientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID,
    },
    facebook: {
      clientId: import.meta.env.VITE_FACEBOOK_OAUTH_CLIENT_ID ?? '',
      enabled: !!import.meta.env.VITE_FACEBOOK_OAUTH_CLIENT_ID,
    },
  },
  features: {
    imageSearch: {
      enabled: import.meta.env.VITE_ENABLE_IMAGE_SEARCH === 'true',
    },
    ai: {
      enabled: import.meta.env.VITE_ENABLE_AI === 'true',
    },
    inlineEditing: {
      enabled: !(import.meta.env.VITE_ENABLE_INLINE_EDITING === 'false'),
    },
  },
  defaults: {
    preferredWeightUnit: 'g' as TGearWeightUnit,
  },
  storage: {
    // Maximum file size for regular users (20 MB)
    maxFileSize: import.meta.env.VITE_MAX_FILE_SIZE ? parseInt(import.meta.env.VITE_MAX_FILE_SIZE) : 20 * 1024 * 1024,
    // Maximum file size for administrators (50 MB)
    maxFileSizeAdmin: import.meta.env.VITE_MAX_FILE_SIZE_ADMIN ? parseInt(import.meta.env.VITE_MAX_FILE_SIZE_ADMIN) : 50 * 1024 * 1024,
  },
  sentry: {
    dsn: import.meta.env.VITE_SENTRY_DSN ?? '',
    enabled: !!import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT ?? import.meta.env.MODE ?? 'development',
    tracesSampleRate: import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) : 1.0,
    replaysSessionSampleRate: import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE) : 0.1,
    replaysOnErrorSampleRate: import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE ? parseFloat(import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE) : 1.0,
  },
}

// osobna zmienna do użycia w localStorage / store
export const DARK_MODE_STORAGE_KEY = `${config.app.id}:dark-mode`
export const JWT_STORE_KEY = `${config.app.id}:token`
export const LOCALE_STORAGE_KEY = `${config.app.id}:locale`
export const SETTINGS_STORAGE_KEY = `${config.app.id}:settings`
export const CORE_SETTINGS_STORAGE_KEY = `${config.app.id}:core-settings`
export const GEAR_SETTINGS_STORAGE_KEY = `${config.app.id}:gear-settings`
export const USER_STORAGE_KEY = `${config.app.id}:user`
export const ITEMS_TABLE_COLUMN_VISIBILITY_KEY = `${config.app.id}:items-table-column-visibility`
export const ITEMS_TABLE_EDIT_MODE_KEY = `${config.app.id}:items-table-edit-mode`
export const ALL_ITEMS_TABLE_COLUMN_VISIBILITY_KEY = `${config.app.id}:all-items-table-column-visibility`
export const ALL_ITEMS_PAGE_FILTERS_KEY = `${config.app.id}:all-items-page:filters`
export const SHOPPING_PLANNING_PAGE_FILTERS_KEY = `${config.app.id}:shopping-planning-page:filters`
export const SHOPPING_PLANNING_PAGE_FILTERS_COLLAPSED_KEY = `${config.app.id}:shopping-planning-page:filters-collapsed`
export const CONTAINERS_STORAGE_KEY = `${config.app.id}:containers`
export const CONTAINERS_LIST_PAGE_FILTERS_KEY = `${config.app.id}:containers-list-page:filters`
export const PUBLIC_CONTAINERS_BROWSER_PAGE_FILTERS_KEY = `${config.app.id}:public-containers-browser-page:filters`
export const CATALOGUE_BROWSER_PAGE_FILTERS_KEY = `${config.app.id}:catalogue-browser-page:filters`
export const UPDATE_FROM_CATALOGUE_FIELDS_KEY = `${config.app.id}:update-from-catalogue-fields`
