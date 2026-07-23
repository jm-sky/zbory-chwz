// shared/services/sentry.ts

import * as Sentry from '@sentry/vue'
import { config } from '@/shared/config/config'
import type { App } from 'vue'
import type { Router } from 'vue-router'

/**
 * Initialize Sentry for error tracking and performance monitoring
 *
 * @param app - Vue app instance
 * @param router - Vue Router instance
 */
export function initSentry(app: App, router: Router): void {
  if (!config.sentry.enabled) {
    return
  }

  Sentry.init({
    app,
    dsn: config.sentry.dsn,
    environment: config.sentry.environment,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    // Performance Monitoring
    tracesSampleRate: config.sentry.tracesSampleRate,
    // Session Replay
    replaysSessionSampleRate: config.sentry.replaysSessionSampleRate,
    replaysOnErrorSampleRate: config.sentry.replaysOnErrorSampleRate,
    // Release tracking
    release: __APP_VERSION__,
    // Additional context
    beforeSend(event, hint) {
      // Filter out chunk load errors (handled separately)
      if (event.exception) {
        const error = hint.originalException
        if (
          error instanceof Error &&
          (error.name === 'ChunkLoadError' ||
            error.message?.includes('Failed to fetch dynamically imported module') ||
            error.message?.includes('Importing a module script failed'))
        ) {
          return null // Don't send chunk load errors to Sentry
        }
      }
      return event
    },
  })
}

/**
 * Set user context for Sentry error tracking
 * Call this when a user logs in to associate errors with their account
 *
 * Deliberately excludes email/name — Sentry is a third-party service and
 * session replays/error reports should not carry PII about who is logged in.
 *
 * @param user - User information to set in Sentry context
 */
export function setSentryUser(user: { id: string } | null): void {
  if (!config.sentry.enabled) {
    return
  }

  if (user) {
    Sentry.setUser({
      id: user.id,
    })
  } else {
    Sentry.setUser(null)
  }
}

