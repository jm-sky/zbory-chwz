import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './scripts',
  testMatch: '**/*.ts',
  fullyParallel: false, // Run sequentially to avoid rate limiting
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to avoid rate limiting
  timeout: 600000, // 10 minutes per test (for processing many products)
  reporter: 'list',
  use: {
    baseURL: 'https://militaria.pl',
    trace: 'on-first-retry',
    headless: false, // Show browser for debugging
  },
        projects: [
          {
            name: 'chromium',
            use: {
              ...devices['Desktop Chrome'],
              viewport: { width: 1920, height: 1080 }, // HD resolution
            },
          },
        ],
})

