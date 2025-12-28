import { VitePWA } from 'vite-plugin-pwa'

export const pwaPlugin = VitePWA({
  registerType: 'prompt',
  includeAssets: [
    'icons/icon-48x48.png',
    'icons/icon-72x72.png',
    'icons/icon-96x96.png',
    'icons/icon-128x128.png',
    'icons/icon-144x144.png',
    'icons/icon-152x152.png',
    'icons/icon-192x192.png',
    'icons/icon-256x256.png',
    'icons/icon-384x384.png',
    'icons/icon-512x512.png',
  ],
  manifest: {
    name: 'Gear Stack',
    short_name: 'Gear Stack',
    description: 'Gear Stack for managing survival gear and bug-out bag equipment.',
    theme_color: '#18181b',
    background_color: '#ffffff',
    display: 'standalone',
    orientation: 'portrait',
    scope: '/',
    start_url: '/',
    icons: [
      {
        src: 'icons/icon-48x48.png',
        sizes: '48x48',
        type: 'image/png',
      },
      {
        src: 'icons/icon-72x72.png',
        sizes: '72x72',
        type: 'image/png',
      },
      {
        src: 'icons/icon-96x96.png',
        sizes: '96x96',
        type: 'image/png',
      },
      {
        src: 'icons/icon-128x128.png',
        sizes: '128x128',
        type: 'image/png',
      },
      {
        src: 'icons/icon-144x144.png',
        sizes: '144x144',
        type: 'image/png',
      },
      {
        src: 'icons/icon-152x152.png',
        sizes: '152x152',
        type: 'image/png',
      },
      {
        src: 'icons/icon-192x192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any maskable',
      },
      {
        src: 'icons/icon-256x256.png',
        sizes: '256x256',
        type: 'image/png',
      },
      {
        src: 'icons/icon-384x384.png',
        sizes: '384x384',
        type: 'image/png',
      },
      {
        src: 'icons/icon-512x512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any maskable',
      },
    ],
  },
  workbox: {
    globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
    maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5 MB (default is 2 MB)
    runtimeCaching: [
      {
        urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
        handler: 'CacheFirst',
        options: {
          cacheName: 'google-fonts-cache',
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
          },
          cacheableResponse: {
            statuses: [200],
          },
        },
      },
      {
        urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
        handler: 'CacheFirst',
        options: {
          cacheName: 'gstatic-fonts-cache',
          expiration: {
            maxEntries: 10,
            maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
          },
          cacheableResponse: {
            statuses: [200],
          },
        },
      },
      {
        urlPattern: /^https:\/\/api\./i,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'api-cache',
          expiration: {
            maxEntries: 50,
            maxAgeSeconds: 60 * 5, // 5 minutes
          },
          networkTimeoutSeconds: 10,
          cacheableResponse: {
            statuses: [200],
          },
        },
      },
    ],
  },
  devOptions: {
    enabled: false, // Disable PWA in dev mode for faster development
  },
})


