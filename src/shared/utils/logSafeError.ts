import { isAxiosError } from 'axios'
import { logger } from './logger'

/**
 * Log a caught error without the raw error object — Axios errors carry
 * `error.config.data`/`error.response.data`, which for congregation/contact
 * forms includes the submitted name/phone/address. Only message + status
 * are safe to print to the console.
 */
export const logSafeError = (context: string, error: unknown): void => {
  if (isAxiosError(error)) {
    logger.error(context, { message: error.message, status: error.response?.status })
    return
  }
  logger.error(context, { message: error instanceof Error ? error.message : String(error) })
}
