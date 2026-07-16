import { config, LOCALE_STORAGE_KEY } from '@/shared/config/config'
import type { InternalAxiosRequestConfig } from 'axios'

export function localeInterceptor(axiosConfig: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const locale = localStorage.getItem(LOCALE_STORAGE_KEY) ?? config.i18n.defaultLocale
  axiosConfig.headers['Accept-Language'] = locale

  return axiosConfig
}
