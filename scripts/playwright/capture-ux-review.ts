import { chromium, type Page } from 'playwright'
import path from 'node:path'

const BASE_URL = 'http://localhost:5176'
const ASSETS_DIR = path.join(process.cwd(), 'docs/reviews/assets/2026-07-21--design-ux')
const CONGREGATION_ID = '01KY1SPKX9317P0E6EJN4F6MJ8'
const TEST_EMAIL = 'test@zbory.chwz.waw.pl'
const TEST_PASSWORD = 'Secret123!'

type ViewportName = 'desktop' | 'mobile'

const VIEWPORTS: Record<ViewportName, { width: number, height: number }> = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 375, height: 812 },
}

async function screenshot(page: Page, viewport: ViewportName, name: string, fullPage = true): Promise<void> {
  const filePath = path.join(ASSETS_DIR, viewport, `${viewport}--${name}.png`)
  await page.screenshot({ path: filePath, fullPage })
  console.log(`saved ${filePath}`)
}

async function switchToPolish(page: Page): Promise<void> {
  const plButton = page.getByRole('button', { name: /Switch language to PL|Przełącz język na PL/i })
  if (await plButton.isVisible().catch(() => false)) {
    await plButton.click()
    await page.waitForTimeout(500)
  }
}

async function dismissSessionDialog(page: Page): Promise<void> {
  const closeButton = page.getByRole('button', { name: /Close|Zamknij/i })
  if (await closeButton.isVisible().catch(() => false)) {
    await closeButton.click()
    await page.waitForTimeout(300)
  }
  await page.keyboard.press('Escape').catch(() => undefined)
}

async function captureGuestFlow(page: Page, viewport: ViewportName): Promise<void> {
  const guestRoutes: Array<{ path: string, name: string }> = [
    { path: '/', name: 'landing--guest' },
    { path: '/auth/login', name: 'auth-login--guest' },
    { path: '/auth/register', name: 'auth-register--guest' },
    { path: `/congregations/${CONGREGATION_ID}`, name: 'congregation-detail--guest' },
    { path: '/about', name: 'about--guest' },
    { path: '/privacy', name: 'privacy--guest' },
    { path: '/cookies', name: 'cookies--guest' },
    { path: '/terms', name: 'terms--guest' },
    { path: '/contact', name: 'contact--guest' },
    { path: '/nieistniejaca-strona', name: 'not-found--guest' },
  ]

  for (const route of guestRoutes) {
    await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'networkidle' })
    await dismissSessionDialog(page)
    await page.waitForTimeout(800)
    await screenshot(page, viewport, route.name)
  }

  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' })
  await dismissSessionDialog(page)
  const mapButton = page.getByRole('button', { name: /map|mapa/i }).first()
  if (await mapButton.isVisible().catch(() => false)) {
    await mapButton.click()
    await page.waitForTimeout(1500)
    await screenshot(page, viewport, 'landing-map--guest')
  }
}

async function login(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'networkidle' })
  await page.locator('input[type="email"], input[name="email"]').first().fill(TEST_EMAIL)
  await page.locator('input[type="password"]').first().fill(TEST_PASSWORD)
  await page.getByRole('button', { name: /sign in|zaloguj/i }).click()
  await page.waitForURL((url) => !url.pathname.includes('/auth/login'), { timeout: 15000 })
  await page.waitForTimeout(1000)
}

async function captureAuthFlow(page: Page, viewport: ViewportName): Promise<void> {
  const authRoutes: Array<{ path: string, name: string }> = [
    { path: '/', name: 'landing--logged-in' },
    { path: '/profile', name: 'profile--logged-in' },
    { path: '/profile/edit', name: 'profile-edit--logged-in' },
    { path: '/settings', name: 'settings--logged-in' },
    { path: '/groups', name: 'groups-list--logged-in' },
    { path: '/people-directory', name: 'directory-export--logged-in' },
    { path: '/people-directory/persons', name: 'directory-persons--logged-in' },
    { path: `/congregations/${CONGREGATION_ID}/edit`, name: 'congregation-edit--logged-in' },
    { path: '/admin', name: 'admin-dashboard--logged-in' },
    { path: '/admin/users', name: 'admin-users--logged-in' },
    { path: '/admin/congregations', name: 'admin-congregations--logged-in' },
    { path: '/admin/congregations/import', name: 'admin-import--logged-in' },
    { path: '/admin/share-links', name: 'admin-share-links--logged-in' },
  ]

  for (const route of authRoutes) {
    await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    await screenshot(page, viewport, route.name)
  }

  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /user menu|menu użytkownika/i }).click()
  await page.waitForTimeout(500)
  await screenshot(page, viewport, 'user-menu--logged-in', false)

  const groupLink = page.getByRole('link', { name: /.+/ }).filter({ hasText: /group|grup/i }).first()
  await page.goto(`${BASE_URL}/groups`, { waitUntil: 'networkidle' })
  const firstGroup = page.locator('a[href^="/groups/"]').first()
  if (await firstGroup.isVisible().catch(() => false)) {
    await firstGroup.click()
    await page.waitForTimeout(1000)
    await screenshot(page, viewport, 'groups-detail--logged-in')
  }
}

async function runViewport(viewport: ViewportName): Promise<void> {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: VIEWPORTS[viewport],
    colorScheme: 'light',
    locale: 'pl-PL',
  })
  const page = await context.newPage()

  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await switchToPolish(page)
  await captureGuestFlow(page, viewport)

  await login(page)
  await captureAuthFlow(page, viewport)

  await browser.close()
}

async function main(): Promise<void> {
  console.log('Capturing UX review screenshots...')
  await runViewport('desktop')
  await runViewport('mobile')
  console.log('Done.')
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
