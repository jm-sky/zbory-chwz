/**
 * Script to find products on militaria.pl and collect their URLs
 *
 * Usage (with environment variables - RECOMMENDED):
 *   FILTER="Ka-Bar" pnpm playwright test find-militaria-products.ts
 *   FILTER="ESEE Izula" DEBUG=true pnpm playwright test find-militaria-products.ts
 *   DEBUG=true pnpm playwright test find-militaria-products.ts
 *
 * Usage (Windows PowerShell):
 *   $env:FILTER="Ka-Bar"; pnpm playwright test find-militaria-products.ts
 *   $env:DEBUG="true"; $env:FILTER="Ka-Bar"; pnpm playwright test find-militaria-products.ts
 *
 * Usage (Windows CMD):
 *   set FILTER=Ka-Bar && pnpm playwright test find-militaria-products.ts
 *   set DEBUG=true && set FILTER=Ka-Bar && pnpm playwright test find-militaria-products.ts
 *
 * Note: Playwright does NOT pass custom arguments (--filter, --debug) after -- to process.argv.
 * You MUST use environment variables instead.
 *
 * Options:
 *   FILTER=<value>: Filter products by name, brand, or model (case-insensitive)
 *   DEBUG=true or DEBUG=1: Enable detailed debug logging for scoring algorithm
 *   DEBUG_ARGS=true: Show raw process.argv for debugging argument parsing
 *
 * The filter matches product name, brand, or model (case-insensitive).
 * Debug mode shows detailed scoring breakdown for each URL (category match, brand match, model match, etc.)
 */

import { test } from '@playwright/test'
import { createWriteStream, readFileSync, writeFileSync } from 'fs'
import { join } from 'path'
import * as readline from 'readline'
// import type { CatalogueItem } from '../backend/app/seeders/catalogue_items.types' // Removed - catalogue seeder deleted
type CatalogueItem = any // Temporary type - catalogue seeder was removed

const MIN_SCORE = 70

/**
 * Normalize Polish diacritics for matching
 * Converts: ą→a, ć→c, ę→e, ł→l, ń→n, ó→o, ś→s, ź→z, ż→z
 */
function normalizePolish(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ą/g, 'a')
    .replace(/ć/g, 'c')
    .replace(/ę/g, 'e')
    .replace(/ł/g, 'l')
    .replace(/ń/g, 'n')
    .replace(/ó/g, 'o')
    .replace(/ś/g, 's')
    .replace(/ź/g, 'z')
    .replace(/ż/g, 'z')
}

/**
 * Category keywords for matching products
 * Used to verify if search results match the product category
 * Note: Keywords include normalized versions (noz = nóż) for URL matching
 */
const CATEGORY_KEYWORDS: Record<string, string[]> = {
  fire: ['zapalniczka', 'zapalniczka', 'lighter', 'zapalki', 'zapałki', 'matches', 'krzesiwo', 'flint', 'fire', 'ogien', 'ogień', 'torch', 'pochodnia'],
  water: ['butelka', 'bottle', 'woda', 'water', 'bidon', 'canteen', 'filt', 'filter'],
  food: ['jedzenie', 'food', 'racja', 'ration', 'menazka', 'menażka', 'mess', 'kubek', 'cup'],
  shelter: ['namiot', 'tent', 'tarp', 'plachta', 'spiwor', 'śpiwór', 'sleeping', 'bag', 'hamak', 'hammock'],
  light: ['latarka', 'flashlight', 'czolowka', 'czołówka', 'headlamp', 'baterie', 'batteries'],
  blades: ['noz', 'nóż', 'noze', 'noże', 'knife', 'knives', 'blade', 'blades', 'maczeta', 'maczety', 'machete', 'siekiera', 'siekery', 'axe', 'axes', 'toporek', 'toporki', 'hatchet', 'hatchets', 'sword', 'swords'],
  tools: ['knife', 'multitool', 'multitools', 'scyzoryk', 'siekiera', 'siekery', 'axe', 'axes', 'pila', 'piła', 'saw', 'kompas', 'compass', 'tool', 'tools', 'shovel', 'saperka', 'lopata', 'łopata'],
  firstAid: ['apteczka', 'first', 'aid', 'bandaz', 'bandaż', 'bandage', 'plaster', 'gazik'],
  navigation: ['kompas', 'compass', 'mapa', 'map', 'gps', 'lornetka', 'binoculars'],
  communication: ['radio', 'telefon', 'phone', 'powerbank', 'ladowarka', 'ładowarka', 'charger'],
  other: [],
}

interface ProductLink {
  url: string
  price?: number
  variant?: string
}

interface SearchResult {
  productId: string
  productName: string
  foundUrls: ProductLink[]
}

interface ScoreDebugDetails {
  category?: { matched: boolean; score: number; keywords?: string[] }
  brand?: { matched: boolean; score: number; brand?: string }
  model?: { matched: boolean; score: number; exactMatch?: boolean; model?: string; words?: string[]; matchPercentage?: string; missingWords?: string[]; missingWordsPenalty?: number; percentagePenalty?: number; perfectMatchBonus?: number }
  name?: { matches: number; score: number; words?: string[] }
  query?: { matches: number; score: number; words?: string[] }
  generic?: { matches: number; penalty: number; words?: string[] }
  replacement?: { excluded: boolean; keywords?: string[] }
}

interface ScoredLink {
  productLink: ProductLink
  score: number
  reason: string
  debugDetails?: ScoreDebugDetails
}

/**
 * Parse command line arguments from process.argv
 *
 * NOTE: Playwright does NOT pass custom arguments after -- to process.argv.
 * This function tries to parse them, but environment variables are preferred.
 *
 * Supports: --filter=value, --filter value, --debug
 */
function parseArgs(): { filter?: string; debug?: boolean } {
  const args: { filter?: string; debug?: boolean } = {}

  // Debug: log all argv to see what Playwright passes
  if (process.env.DEBUG_ARGS === 'true') {
    console.log('DEBUG: process.argv =', process.argv)
    console.log('DEBUG: process.argv.slice(2) =', process.argv.slice(2))
    console.log('DEBUG: Note: Playwright may not pass custom args after --')
  }

  const argv = process.argv.slice(2)

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]

    // Handle --filter=value format
    if (arg.startsWith('--filter=')) {
      args.filter = arg.split('=')[1]
      // Remove quotes if present
      if (args.filter && (args.filter.startsWith('"') || args.filter.startsWith("'"))) {
        args.filter = args.filter.slice(1, -1)
      }
    }
    // Handle --filter value format
    else if (arg === '--filter' && i + 1 < argv.length) {
      args.filter = argv[i + 1]
      // Remove quotes if present
      if (args.filter && (args.filter.startsWith('"') || args.filter.startsWith("'"))) {
        args.filter = args.filter.slice(1, -1)
      }
      i++ // Skip next argument as it's the value
    }
    // Handle --debug flag
    else if (arg === '--debug' || arg === '-d') {
      args.debug = true
    }
  }

  return args
}

/**
 * Load products from JSON file
 */
function loadProductsFromJson(jsonPath: string): CatalogueItem[] {
  const content = readFileSync(jsonPath, 'utf-8')
  return JSON.parse(content) as CatalogueItem[]
}

/**
 * Generate search query for a product
 */
function generateSearchQuery(product: CatalogueItem): string {
  // Try brand + model first (only if brand is not Generic)
  if (product.brand && product.brand !== 'Generic' && product.brand !== 'Generic / MIL-SPEC') {
    if (product.model && product.model.trim()) {
      const query = `${product.brand} ${product.model}`.trim()
      if (query) return query
    }
    // If model is missing/empty, try just brand
    if (product.brand.trim()) return product.brand.trim()
  }

  // Fallback to product name
  if (product.name && product.name.trim()) {
    return product.name.trim()
  }

  // Last resort: use brand or model if available
  if (product.brand && product.brand.trim()) return product.brand.trim()
  if (product.model && product.model.trim()) return product.model.trim()

  // Should never happen, but return empty string as fallback
  console.warn(`Warning: No search query could be generated for product ${product.id}`)
  return ''
}

/**
 * Update catalogue_items.json with found URLs
 */
function updateJsonFile(jsonPath: string, results: SearchResult[]): void {
  try {
    const products = JSON.parse(readFileSync(jsonPath, 'utf-8')) as CatalogueItem[]

    let updatedCount = 0
    for (const result of results) {
      const product = products.find(p => p.id === result.productId)
      if (product) {
        if (result.foundUrls.length === 0) {
          // Mark product as processed by setting empty shops array
          // This prevents reprocessing the same product
          product.shops = []
          updatedCount++
        } else {
          // Map ProductLink to shop format with price and variant
          product.shops = result.foundUrls.map(productLink => {
            const shop: { url: string; variant?: string; price?: number; currency?: string } = {
              url: productLink.url
            }
            if (productLink.variant) {
              shop.variant = productLink.variant
            }
            if (productLink.price) {
              shop.price = productLink.price
              shop.currency = 'PLN'
            }
            return shop
          })
          updatedCount++
        }
      }
    }

    writeFileSync(jsonPath, JSON.stringify(products, null, 2), 'utf-8')
    console.log(`Updated ${updatedCount} products in JSON file`)
  } catch (error) {
    console.error('Error updating JSON file:', error)
  }
}


test.describe('Find products on militaria.pl', () => {
  test('Search and collect product URLs', async ({ page }) => {
    const jsonPath = join(process.cwd(), 'backend/app/seeders/catalogue_items.json')

    // Parse command line arguments (Playwright may not pass them - use env vars instead)
    const args = parseArgs()

    // Use environment variables (preferred) or fall back to parsed args
    // NOTE: Playwright does NOT pass custom arguments after -- to process.argv
    // You MUST use environment variables: FILTER="Ka-Bar" pnpm playwright test ...
    const FILTER = process.env.FILTER ?? args.filter
    const DEBUG = (process.env.DEBUG === 'true' || process.env.DEBUG === '1') || (args.debug ?? false)

    // Setup log file for DEBUG mode
    let logFileStream: ReturnType<typeof createWriteStream> | null = null
    const originalConsoleLog = console.log
    const originalConsoleError = console.error
    const originalConsoleWarn = console.warn

    if (DEBUG) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const logFileName = `find-militaria-products-debug-${timestamp}.log`
      const logFilePath = join(process.cwd(), logFileName)
      logFileStream = createWriteStream(logFilePath, { flags: 'w', encoding: 'utf-8' })

      // Write header to log file
      logFileStream.write(`=== Debug Log Started at ${new Date().toISOString()} ===\n`)
      logFileStream.write(`Filter: ${FILTER ?? 'none'}\n`)
      logFileStream.write(`JSON Path: ${jsonPath}\n`)
      logFileStream.write(`${'='.repeat(80)}\n\n`)

      // Override console methods to write to both stdout and file
      console.log = (...args: unknown[]) => {
        const message = args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg, null, 2)).join(' ')
        originalConsoleLog(...args)
        if (logFileStream) {
          logFileStream.write(`${message}\n`)
        }
      }

      console.error = (...args: unknown[]) => {
        const message = args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg, null, 2)).join(' ')
        originalConsoleError(...args)
        if (logFileStream) {
          logFileStream.write(`[ERROR] ${message}\n`)
        }
      }

      console.warn = (...args: unknown[]) => {
        const message = args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg, null, 2)).join(' ')
        originalConsoleWarn(...args)
        if (logFileStream) {
          logFileStream.write(`[WARN] ${message}\n`)
        }
      }

      console.log(`🐛 DEBUG MODE: Logging to file: ${logFileName}`)
    }

    // Cleanup function to restore console and close file
    const cleanup = () => {
      if (logFileStream) {
        logFileStream.write(`\n${'='.repeat(80)}\n`)
        logFileStream.write(`=== Debug Log Ended at ${new Date().toISOString()} ===\n`)
        logFileStream.end()
        logFileStream = null
      }
      console.log = originalConsoleLog
      console.error = originalConsoleError
      console.warn = originalConsoleWarn
    }

    try {
      // Debug: show what was parsed and what will be used
    if (process.env.DEBUG_ARGS === 'true' || DEBUG) {
      console.log('DEBUG: Parsed args from process.argv =', args)
      console.log('DEBUG: process.env.FILTER =', process.env.FILTER)
      console.log('DEBUG: process.env.DEBUG =', process.env.DEBUG)
      console.log('DEBUG: Final FILTER =', FILTER)
      console.log('DEBUG: Final DEBUG =', DEBUG)
      if (args.filter && !process.env.FILTER) {
        console.log('⚠️  WARNING: --filter argument was parsed but may not work with Playwright.')
        console.log('⚠️  Use environment variable instead: FILTER="Ka-Bar" pnpm playwright test ...')
      }
    }

    // STEP-BY-STEP MODE: Set to true for interactive debugging
    const STEP_BY_STEP = process.env.STEP_BY_STEP === 'true' || process.env.STEP_BY_STEP === '1'
    const MAX_PRODUCTS = process.env.MAX_PRODUCTS ? parseInt(process.env.MAX_PRODUCTS, 10) : (STEP_BY_STEP ? 1 : undefined)
    const INTERACTIVE = process.env.INTERACTIVE === 'true' || process.env.INTERACTIVE === '1'

    // Create readline interface for interactive mode
    let rl: readline.Interface | null = null
    if (INTERACTIVE) {
      rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
      })
    }

      const allProducts = loadProductsFromJson(jsonPath)

      // Show debug mode status
      if (DEBUG) {
        console.log('🐛 DEBUG MODE: Detailed scoring information will be shown\n')
      }

    // Apply filter if provided (matches name, brand, or model)
    let filteredProducts = allProducts
    if (FILTER) {
      const filterLower = FILTER.toLowerCase()
      filteredProducts = allProducts.filter(p => {
        const nameMatch = p.name?.toLowerCase().includes(filterLower) ?? false
        const brandMatch = p.brand?.toLowerCase().includes(filterLower) ?? false
        const modelMatch = p.model?.toLowerCase().includes(filterLower) ?? false
        return nameMatch || brandMatch || modelMatch
      })
      console.log(`🔍 Filter applied: "${FILTER}"`)
      console.log(`   Found ${filteredProducts.length} product(s) matching filter`)
    }

    // Filter products that need shop URLs:
    // - products without shops property (undefined/null) → need processing
    // - products with empty shops array [] → need processing (may have been processed incorrectly)
    // - products with shops array containing items → already processed, has results → skip
    let products = filteredProducts.filter(p => {
      if (!p.shops) return true // undefined or null → needs processing
      if (Array.isArray(p.shops) && p.shops.length === 0) return true // empty array → needs processing
      if (Array.isArray(p.shops) && p.shops.length > 0) return false // has shops → already processed, skip
      return true // fallback: process if unsure
    })

    if (MAX_PRODUCTS) {
      products = products.slice(0, MAX_PRODUCTS)
      console.log(`🧪 STEP-BY-STEP MODE: Processing only ${products.length} product(s)`)
      if (products.length > 0) {
        console.log(`   Product to process: ${products[0].name} (${products[0].id})`)
      }
    } else {
      console.log(`Found ${products.length} products needing shop URLs`)
    }

    const results: SearchResult[] = []

      for (let idx = 0; idx < products.length; idx++) {
        const product = products[idx]

        if (INTERACTIVE && idx > 0) {
          console.log('\n⏸️  Press Enter to continue to next product...')
        await new Promise<void>(resolve => {
          if (rl) {
            rl.question('', () => {
              resolve()
            })
          } else {
            setTimeout(resolve, 5000) // Fallback timeout
          }
        })
      } else if (STEP_BY_STEP && idx > 0) {
        console.log('\n⏸️  Waiting 5 seconds before next product...')
        await new Promise(resolve => setTimeout(resolve, 5000))
      }

      console.log(`\n${'='.repeat(80)}`)
      console.log(`Product ${idx + 1}/${products.length}: ${product.name}`)
      console.log(`${'='.repeat(80)}`)
      const searchQuery = generateSearchQuery(product)

      // Skip if query is empty
      if (!searchQuery || searchQuery.trim() === '') {
        console.warn(`\n⚠️  Skipping ${product.name} - empty search query`)
        results.push({
          productId: product.id,
          productName: product.name,
          foundUrls: []
        })
        continue
      }

      const encodedQuery = encodeURIComponent(searchQuery)
      // Use pref_q parameter instead of q (as per site structure)
      const searchUrl = `https://militaria.pl/szukaj?pref_q=${encodedQuery}`

      console.log('\n🔍 Step 1: Generating search query')
      console.log(`   Product: ${product.name}`)
      console.log(`   Brand: ${product.brand ?? 'N/A'}`)
      console.log(`   Model: ${product.model ?? 'N/A'}`)
      console.log(`   Query: "${searchQuery}" (length: ${searchQuery.length})`)
      console.log(`   URL: ${searchUrl}`)

      // Debug: verify query is not empty
      if (!searchQuery || searchQuery.trim() === '') {
        console.error(`  ❌ ERROR: Empty search query for ${product.name}!`)
        console.error(`  Product data: name="${product.name}", brand="${product.brand}", model="${product.model}"`)
      }

      if (INTERACTIVE) {
        console.log('\n⏸️  Press Enter to navigate to search page...')
        await new Promise<void>(resolve => {
          if (rl) {
            rl.question('', () => {
              resolve()
            })
          } else {
            setTimeout(resolve, 3000) // Fallback timeout
          }
        })
      } else if (STEP_BY_STEP) {
        console.log('\n⏸️  Waiting 3 seconds before navigation...')
        await new Promise(resolve => setTimeout(resolve, 3000))
      }

      try {
        console.log('\n🌐 Step 2: Navigating to search page')
        await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 })
        console.log(`   ✅ Page loaded: ${page.url()}`)

        // Handle cookie consent (Cookiebot) - only if not already accepted
        let cookieClicked = false
        try {
          // Check if cookie consent was already accepted (check for Cookiebot cookie or dialog absence)
          const cookieAlreadyAccepted = await page.evaluate(() => {
            // Check if Cookiebot cookie exists (indicates consent was given)
            return document.cookie.includes('Cookiebot') ||
                   document.cookie.includes('cookiebot') ||
                   // Check if dialog is already hidden/not present
                   !document.querySelector('#CybotCookiebotDialog')
          })

          if (!cookieAlreadyAccepted) {

            const cookieSelectors = [
              '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
              '#CybotCookiebotDialogBodyButtonAccept',
              'button[id*="CybotCookiebotDialog"][id*="Allow"]',
              'button[id*="CybotCookiebotDialog"][id*="Accept"]',
              '[id*="cookiebot"] button[id*="allow"]',
              '[id*="cookiebot"] button[id*="accept"]',
              'button:has-text("Accept all")',
              'button:has-text("Akceptuj wszystkie")',
              'button:has-text("Allow all")',
            ]

            // Try to find cookie button with short timeout (dialog appears quickly if it will appear)
            for (const selector of cookieSelectors) {
              try {
                // Wait for selector to appear (with short timeout - if it doesn't appear quickly, it won't appear)
                const cookieButton = await page.waitForSelector(selector, {
                  state: 'visible',
                  timeout: 1000 // Reduced from 3000ms - if dialog doesn't appear in 1s, it's probably not coming
                }).catch(() => null)

                if (cookieButton) {
                  await cookieButton.click()
                  cookieClicked = true
                  // Wait for dialog to disappear
                  await page.waitForSelector(selector, { state: 'hidden', timeout: 2000 }).catch(() => {})
                  break
                }
              } catch {
                // Try next selector
              }
            }
          }

          // Small delay after cookie handling
          if (cookieClicked) {
            await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {})
          }
        } catch {
          // Cookie consent not found or already accepted, continue
        }

        // Wait for search results container to appear (prefixbox structure)
        let productLinks: Array<{ url: string; price?: number; variant?: string }> = []
        try {
          // Wait for prefixbox results container or any product elements (longer timeout)
          try {
            await page.waitForSelector('#prefixbox-results, li[data-product-id], .prefixbox-product-container-wrapper', { timeout: 25000 })
          } catch {
            // Try waiting for any product links
            await page.waitForSelector('a[href*="/p/"]', { timeout: 10000 }).catch(() => null)
          }

          // Additional wait for products to render (shorter wait for async loading)
          await page.waitForTimeout(1500) // Reduced from 4000ms to 1500ms
          await page.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => {}) // Changed from networkidle to domcontentloaded, shorter timeout

          // Look for product links in prefixbox structure with price and variant extraction
          productLinks = await page.evaluate(() => {
            const results: Array<{ url: string; price?: number; variant?: string }> = []

            // Find prefixbox results container or use body as fallback
            let resultsContainer = document.querySelector('#prefixbox-results')
            if (!resultsContainer) {
              // Try to find any product container
              resultsContainer = document.querySelector('.prefixbox-products-container') ?? document.body
              console.log('  [DEBUG] Using fallback container')
            }

            // Try multiple selectors to find product links
            const selectors = [
              '.prefixbox-product-container-wrapper a.product-item-link',
              '.prefixbox-product-container-wrapper a.product.photo.product-item-photo',
              'li[data-product-id] a.product-item-link',
              'li[data-product-id] a.product.photo',
              '#prefixbox-results a[href*="/p/"]',
              'main a[href*="/p/"]' // Fallback to main container
            ]

            const foundUrls = new Set<string>()

            for (const selector of selectors) {
              const links = resultsContainer.querySelectorAll<HTMLAnchorElement>(selector)
              if (links.length > 0) {
                console.log(`  [DEBUG] Found ${links.length} links with selector: ${selector}`)

                links.forEach(link => {
                  const href = link.href
                  // Only include product URLs (containing /p/) and exclude search/category pages
                  if (href && href.includes('/p/') && !href.includes('/szukaj') && !href.includes('/kategoria')) {
                    if (!foundUrls.has(href)) {
                      foundUrls.add(href)

                      // Extract price from product card (in PLN)
                      let price: number | undefined
                      const productCard = link.closest('li[data-product-id]') ?? link.closest('.prefixbox-product-container-wrapper')
                      if (productCard) {
                        // Look for price element - prefer PLN price container
                        const plnPriceContainer = productCard.querySelector('.pfbx-price-container.pln')
                        const priceElement = plnPriceContainer?.querySelector('.price, .price-wrapper, [data-price-amount]') ??
                                          productCard.querySelector('.price, .price-wrapper, [data-price-amount]')

                        if (priceElement) {
                          const priceText = priceElement.textContent ?? ''
                          const priceAttr = priceElement.getAttribute('data-price-amount')

                          // Try data-price-amount first (most reliable)
                          if (priceAttr) {
                            // Format: "99,95" or "99.95"
                            const normalized = priceAttr.replace(',', '.')
                            price = parseFloat(normalized)
                          } else {
                            // Parse from text (e.g., "99,95 zł" -> 99.95)
                            // Match: digits, optional comma/dot, optional digits, optional currency
                            const priceMatch = priceText.match(/(\d+)[,\s\.](\d{2})/)
                            if (priceMatch) {
                              const whole = priceMatch[1]
                              const decimal = priceMatch[2]
                              price = parseFloat(`${whole}.${decimal}`)
                            } else {
                              // Try simple number match
                              const simpleMatch = priceText.match(/(\d+)/)
                              if (simpleMatch) {
                                price = parseFloat(simpleMatch[1])
                              }
                            }
                          }
                        }
                      }

                      // Extract variant from product name/link text
                      // Variant is extracted if product name ends with "- Color" pattern
                      let variant: string | undefined
                      const linkText = link.textContent?.trim() ?? ''
                      const hrefSlug = href.split('/p/').pop()?.split('?')[0] ?? ''

                      // Color tokens to match (Olive, Black, Green, Khaki, Coyote)
                      const colorTokens = ['olive', 'black', 'green', 'khaki', 'coyote', 'red', 'blue', 'tan', 'brown', 'grey', 'gray', 'white', 'orange', 'midnight', 'od-green', 'polar-white', 'nordic-noir', 'silver', 'gold']

                      // Check if product name ends with "- Color" pattern
                      const nameMatch = linkText.match(/\s*-\s*([^-]+)$/i)
                      if (nameMatch) {
                        const potentialVariant = nameMatch[1].trim().toLowerCase()
                        // Check if it matches any color token
                        for (const color of colorTokens) {
                          if (potentialVariant === color || potentialVariant.includes(color) || color.includes(potentialVariant)) {
                            // Capitalize first letter of each word
                            variant = color.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                            break
                          }
                        }
                      }

                      // Fallback: check last part of slug
                      if (!variant) {
                        const slugParts = hrefSlug.split('-')
                        const lastPart = slugParts[slugParts.length - 1]?.toLowerCase()
                        for (const color of colorTokens) {
                          if (lastPart === color || lastPart?.includes(color)) {
                            variant = color.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                            break
                          }
                        }
                      }

                      results.push({ url: href, price, variant })
                    }
                  }
                })

                if (results.length >= 5) break // Stop if we found enough links
              }
            }

            console.log(`  [DEBUG] Total unique URLs found: ${results.length}`)
            return results.slice(0, 5) // Get first 5 unique results
          })

          console.log(`\n📦 Step 5: Extracted ${productLinks.length} product link(s)`)
          if (productLinks.length > 0) {
            productLinks.forEach((link, i) => {
              const priceInfo = link.price ? ` (${link.price} PLN)` : ''
              const variantInfo = link.variant ? ` [${link.variant}]` : ''
              console.log(`   ${i + 1}. ${link.url}${priceInfo}${variantInfo}`)
            })
          }
        } catch (error) {
          console.log(`\n❌ Error finding products: ${error}`)
          // No products found, continue with empty array
          productLinks = []
        }

        // Filter and score URLs to find best matches
        if (productLinks.length > 0) {
          console.log('\n🎯 Step 6: Filtering and scoring URLs')
          console.log(`   Found ${productLinks.length} URLs before filtering`)

          const searchQueryLower = searchQuery.toLowerCase()
          const productNameWords = product.name.toLowerCase().split(' ').filter((w: string) => w.length > 3)
          const brandLower = product.brand?.toLowerCase() ?? ''
          const modelLower = product.model?.toLowerCase() ?? ''

          // Keywords that indicate replacement parts or accessories (exclude these)
          const excludeKeywords = [
            'wymienne', 'replacement', 'parts', 'part', 'akcesoria', 'accessories',
            'przecinaki', 'blade', 'blades', 'noze', 'knife', 'knives',
            'osprzet', 'equipment', 'zestaw-czesci', 'parts-kit'
          ]

          // Category-specific keywords for matching
          const categoryKeywords = CATEGORY_KEYWORDS[product.category] ?? []
          // const categoryLower = product.category.toLowerCase()

          // Score and filter URLs
          // Score range: -45 to ~140 (theoretical), typical range: 0-100
          // Score components:
          //   - Replacement parts: -1 (excluded immediately)
          //   - Category mismatch: -20, match: +15
          //   - Brand mismatch: -5, match: +10, brand at slug start: +5 (total: -5 to +15)
          //   - Model exact match: +30, model in slug: +20, generic penalty: -10 (total: -10 to +50)
          //   - Name words: +4 per word (typical: 0-40)
          //   - Query words: +2 per word (typical: 0-20)
          //   - Generic words penalty: -1 per word (typical: 0-10)
          // Minimum accepted score (MIN_SCORE): 50
          const scoredLinks = productLinks.map(productLink => {
            const url = productLink.url
            const urlLower = url.toLowerCase()
            const urlSlug = url.split('/p/').pop()?.split('?')[0] ?? ''

            // Debug details structure
            const debugDetails: ScoreDebugDetails = {}

            // Exclude replacement parts and accessories
            const isReplacementPart = excludeKeywords.some(keyword => urlLower.includes(keyword))
            if (isReplacementPart) {
              const matchedKeywords = excludeKeywords.filter(keyword => urlLower.includes(keyword))
              if (DEBUG) {
                debugDetails.replacement = { excluded: true, keywords: matchedKeywords }
              }
              return { productLink, score: -1, reason: 'replacement part/accessory', debugDetails }
            }

            let score = 0

            // Normalize URL for category matching (handle Polish diacritics)
            const urlLowerNormalized = normalizePolish(urlLower)

            // CRITICAL: Check if URL matches product category (highest priority check)
            // Check both normalized and original keywords
            const matchedCategoryKeywords = categoryKeywords.filter(keyword => {
              const keywordLower = keyword.toLowerCase()
              const keywordNormalized = normalizePolish(keywordLower)
              return urlLower.includes(keywordLower) || urlLowerNormalized.includes(keywordNormalized)
            })
            const categoryMatch = matchedCategoryKeywords.length > 0
            if (!categoryMatch && categoryKeywords.length > 0) {
              // Strong penalty if category keywords don't match
              score -= 20
              if (DEBUG) {
                debugDetails.category = {
                  matched: false,
                  score: -20,
                  keywords: categoryKeywords
                }
              }
            } else if (categoryMatch) {
              // Strong bonus for category match
              score += 15
              if (DEBUG) {
                debugDetails.category = {
                  matched: true,
                  score: 15,
                  keywords: matchedCategoryKeywords
                }
              }
            }

            // Score based on brand match (high priority)
            let brandMatch = false
            let brandScore = 0
            if (brandLower && brandLower !== 'generic' && brandLower !== 'generic / mil-spec') {
              brandMatch = urlLower.includes(brandLower)
              if (brandMatch) {
                brandScore += 10
                // Bonus if brand appears early in URL
                if (urlSlug.startsWith(brandLower.split(' ')[0])) {
                  brandScore += 5
                }
              } else {
                // Penalty if brand doesn't match (but only if brand is specific)
                brandScore -= 5
              }
              score += brandScore
              if (DEBUG) {
                debugDetails.brand = {
                  matched: brandMatch,
                  score: brandScore,
                  brand: brandLower
                }
              }
            }

            // Score based on model match (high priority, but penalize generic words)
            let modelMatch = false
            let modelWords: string[] = []
            if (modelLower && modelLower.length > 3) {
              modelWords = modelLower.split(' ').filter((w: string) => w.length > 2)
              // Penalize generic model words like "classic", "standard", "basic"
              const genericModelWords = ['classic', 'standard', 'basic', 'regular', 'normal', 'simple']
              const isGenericModel = genericModelWords.some(gw => modelLower.includes(gw))

              // Generic/short words to exclude from penalty (don't penalize for missing these)
              const excludedWords = ['the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by']
              const significantModelWords = modelWords.filter(w => w.length >= 3 && !excludedWords.includes(w.toLowerCase()))

              // Check for exact model match in URL (highest priority for model)
              const exactModelMatch = urlLower.includes(modelLower)
              modelMatch = exactModelMatch || modelWords.some(word => urlLower.includes(word))
              let modelScore = 0
              if (exactModelMatch) {
                modelScore += 30 // Big bonus for exact model match
                // Extra bonus if model appears as a complete word in slug
                const modelInSlug = urlSlug.includes(modelLower) || urlSlug.includes(modelLower.replace(/\s+/g, '-'))
                if (modelInSlug) {
                  modelScore += 20 // Even bigger bonus if model is in slug
                }
              }

              if (isGenericModel) {
                // Only give small score for generic model words
                const modelMatches = modelWords.filter(word => urlLower.includes(word) && !genericModelWords.includes(word)).length
                modelScore += modelMatches * 2
                // Penalty if only generic words match
                if (modelWords.every(word => genericModelWords.includes(word))) {
                  modelScore -= 10
                }
              } else {
                // Normal scoring for specific model words (but less if exact match already scored)
                if (!exactModelMatch) {
                  const modelMatches = modelWords.filter(word => urlLower.includes(word)).length
                  modelScore += modelMatches * 8 // Increased from 5 to 8
                } else {
                  // Partial matches still get some points
                  const modelMatches = modelWords.filter(word => urlLower.includes(word)).length
                  modelScore += modelMatches * 2
                }
              }

              // Bonus for perfect model match (100% of significant words matched)
              if (!exactModelMatch && significantModelWords.length > 0) {
                const matchedSignificantWords = significantModelWords.filter(word => urlLower.includes(word))
                const matchPercentage = (matchedSignificantWords.length / significantModelWords.length) * 100

                // Bonus for 100% match of significant words
                if (matchPercentage === 100) {
                  const perfectMatchBonus = 15
                  modelScore += perfectMatchBonus

                  if (DEBUG) {
                    if (!debugDetails.model) {
                      const matchedModelWords = modelWords.filter(word => urlLower.includes(word))
                      debugDetails.model = {
                        matched: true,
                        score: 0,
                        exactMatch: false,
                        model: modelLower,
                        words: matchedModelWords
                      }
                    }
                    debugDetails.model.perfectMatchBonus = perfectMatchBonus
                    debugDetails.model.matchPercentage = '100.0'
                  }
                }
              }

              // Penalty for missing model words (only for significant words, not generic/short ones)
              if (!exactModelMatch && significantModelWords.length > 0) {
                const matchedSignificantWords = significantModelWords.filter(word => urlLower.includes(word))
                const missingSignificantWords = significantModelWords.filter(word => !urlLower.includes(word))

                // Calculate match percentage
                const matchPercentage = (matchedSignificantWords.length / significantModelWords.length) * 100

                // Penalty if match percentage is below threshold (50-80%)
                if (matchPercentage < 100) {
                  // Penalty increases as match percentage decreases
                  let percentagePenalty = 0
                  if (matchPercentage < 50) {
                    percentagePenalty = -15 // Strong penalty for < 50% match
                  } else if (matchPercentage < 60) {
                    percentagePenalty = -10 // Medium penalty for < 60% match
                  } else if (matchPercentage < 80) {
                    percentagePenalty = -5 // Small penalty for < 80% match
                  }

                  if (percentagePenalty !== 0) {
                    modelScore += percentagePenalty

                    if (DEBUG) {
                      if (!debugDetails.model) {
                        const matchedModelWords = modelWords.filter(word => urlLower.includes(word))
                        debugDetails.model = {
                          matched: matchedModelWords.length > 0 || exactModelMatch,
                          score: 0,
                          exactMatch: exactModelMatch,
                          model: modelLower,
                          words: matchedModelWords
                        }
                      }
                      debugDetails.model.percentagePenalty = percentagePenalty
                      debugDetails.model.matchPercentage = matchPercentage.toFixed(1)
                    }
                  }

                  // Additional penalty for each missing significant word (-15 per word, increased from -8)
                  if (missingSignificantWords.length > 0) {
                    const missingWordsPenalty = missingSignificantWords.length * -15
                    modelScore += missingWordsPenalty

                    if (DEBUG) {
                      if (!debugDetails.model) {
                        const matchedModelWords = modelWords.filter(word => urlLower.includes(word))
                        debugDetails.model = {
                          matched: matchedModelWords.length > 0 || exactModelMatch,
                          score: 0,
                          exactMatch: exactModelMatch,
                          model: modelLower,
                          words: matchedModelWords
                        }
                      }
                      debugDetails.model.missingWords = missingSignificantWords
                      debugDetails.model.missingWordsPenalty = missingWordsPenalty
                    }
                  }
                }
              }

              score += modelScore
              if (DEBUG) {
                const matchedModelWords = modelWords.filter(word => urlLower.includes(word))
                if (!debugDetails.model) {
                  debugDetails.model = {
                    matched: matchedModelWords.length > 0 || exactModelMatch,
                    score: modelScore,
                    exactMatch: exactModelMatch,
                    model: modelLower,
                    words: matchedModelWords
                  }
                } else {
                  // Update existing model debug details
                  debugDetails.model.score = modelScore
                  debugDetails.model.matched = matchedModelWords.length > 0 || exactModelMatch
                  debugDetails.model.words = matchedModelWords
                }
              }
            }

            // Bonus for brand + model combination match (strong signal)
            // This gives extra points when both brand and model are found together
            if (brandMatch && modelMatch && modelLower && modelLower.length > 3) {
              const brandModelBonus = 20
              score += brandModelBonus
              if (DEBUG) {
                // Add bonus info to debug details
                if (debugDetails.brand) {
                  debugDetails.brand.score = (debugDetails.brand.score ?? 0) + brandModelBonus
                }
                if (debugDetails.model) {
                  debugDetails.model.score = (debugDetails.model.score ?? 0) + brandModelBonus
                }
              }
            }

            // Score based on product name words (excluding generic words)
            const genericNameWords = ['classic', 'standard', 'basic', 'regular', 'normal', 'simple', 'black', 'green', 'red', 'blue', 'olive', 'tan', 'brown']
            const specificNameWords = productNameWords.filter((w: string) => !genericNameWords.includes(w))
            const matchedNameWords = specificNameWords.filter((word: string) => urlLower.includes(word))
            const nameMatches = matchedNameWords.length
            const nameScore = nameMatches * 4
            score += nameScore
            if (DEBUG) {
              debugDetails.name = {
                matches: nameMatches,
                score: nameScore,
                words: matchedNameWords
              }
            }

            // Score based on query words (excluding generic words)
            const queryWords = searchQueryLower.split(' ').filter(w => w.length > 3 && !genericNameWords.includes(w))
            const matchedQueryWords = queryWords.filter(word => urlLower.includes(word))
            const queryMatches = matchedQueryWords.length
            const queryScore = queryMatches * 2
            score += queryScore
            if (DEBUG) {
              debugDetails.query = {
                matches: queryMatches,
                score: queryScore,
                words: matchedQueryWords
              }
            }

            // Additional penalty for generic words that might cause false matches
            const genericWords = ['black', 'green', 'red', 'blue', 'olive', 'tan', 'brown', 'z-kabura', 'kurtka', 'buty', 'polar']
            const matchedGenericWords = genericWords.filter(word => urlLower.includes(word))
            const genericMatches = matchedGenericWords.length
            const genericPenalty = genericMatches * 1
            score -= genericPenalty
            if (DEBUG && genericMatches > 0) {
              debugDetails.generic = {
                matches: genericMatches,
                penalty: genericPenalty,
                words: matchedGenericWords
              }
            }

            return { productLink, score, reason: 'scored', debugDetails }
          })

          // Filter out negative scores and require minimum score
          const validLinks = scoredLinks
            .filter(item => item.score >= MIN_SCORE && item.productLink)
            .sort((a, b) => b.score - a.score) as ScoredLink[]

          // Helper function to log debug details (defined before use)
          const logDebugDetails = (item: ScoredLink) => {
              if (!DEBUG || !item.debugDetails) return

              const slug = item.productLink.url.split('/p/').pop()?.split('?')[0] ?? ''
              console.log(`\n    🔍 DEBUG Details for: ${slug}`)
              console.log(`       URL: ${item.productLink.url}`)
              console.log(`       Total Score: ${item.score.toFixed(1)}`)

              const d = item.debugDetails

              if (d.category) {
                console.log(`       Category: ${d.category.matched ? '✅' : '❌'} ${d.category.score > 0 ? '+' : ''}${d.category.score} (keywords: ${d.category.keywords?.join(', ') || 'none'})`)
              }

              if (d.brand) {
                console.log(`       Brand: ${d.brand.matched ? '✅' : '❌'} ${d.brand.score > 0 ? '+' : ''}${d.brand.score} (looking for: "${d.brand.brand}")`)
              }

              if (d.model) {
                const perfectMatchLabel = d.model.perfectMatchBonus ? ` (PERFECT MATCH +${d.model.perfectMatchBonus})` : ''
                console.log(`       Model: ${d.model.matched ? '✅' : '❌'} ${d.model.score > 0 ? '+' : ''}${d.model.score} ${d.model.exactMatch ? '(EXACT MATCH)' : ''}${perfectMatchLabel}`)
                if (d.model.words && d.model.words.length > 0) {
                  console.log(`         Matched words: ${d.model.words.join(', ')}`)
                }
                if (d.model.model) {
                  console.log(`         Looking for: "${d.model.model}"`)
                }
                if (d.model.matchPercentage !== undefined) {
                  console.log(`         Match percentage: ${d.model.matchPercentage}%`)
                }
                if (d.model.perfectMatchBonus !== undefined) {
                  console.log(`         Perfect match bonus: +${d.model.perfectMatchBonus}`)
                }
                if (d.model.missingWords && d.model.missingWords.length > 0) {
                  console.log(`         Missing words: ${d.model.missingWords.join(', ')} (penalty: ${d.model.missingWordsPenalty ?? 0})`)
                }
                if (d.model.percentagePenalty !== undefined) {
                  console.log(`         Percentage penalty: ${d.model.percentagePenalty}`)
                }
              }

              if (d.name) {
                console.log(`       Name words: ${d.name.matches > 0 ? '✅' : '❌'} ${d.name.score > 0 ? '+' : ''}${d.name.score} (${d.name.matches} matches)`)
                if (d.name.words && d.name.words.length > 0) {
                  console.log(`         Matched: ${d.name.words.join(', ')}`)
                }
              }

              if (d.query) {
                console.log(`       Query words: ${d.query.matches > 0 ? '✅' : '❌'} ${d.query.score > 0 ? '+' : ''}${d.query.score} (${d.query.matches} matches)`)
                if (d.query.words && d.query.words.length > 0) {
                  console.log(`         Matched: ${d.query.words.join(', ')}`)
                }
              }

              if (d.generic) {
                console.log(`       Generic penalty: ${d.generic.penalty} (${d.generic.matches} matches: ${d.generic.words?.join(', ') || 'none'})`)
              }

              if (d.replacement) {
                console.log(`       Replacement: ${d.replacement.excluded ? '❌ EXCLUDED' : '✅'} (keywords: ${d.replacement.keywords?.join(', ') || 'none'})`)
              }
            }

          // Log all scored links in DEBUG mode (before filtering by threshold)
          if (DEBUG && scoredLinks.length > 0) {
            const allScored = scoredLinks.filter(item => item.productLink).sort((a, b) => b.score - a.score)
            console.log(`\n  📊 All scored URLs (${allScored.length} total):`)
            allScored.forEach((item, idx) => {
              const slug = item.productLink.url.split('/p/').pop()?.split('?')[0] ?? ''
              const priceInfo = item.productLink.price ? ` (${item.productLink.price} PLN)` : ''
              const variantInfo = item.productLink.variant ? ` [${item.productLink.variant}]` : ''
              const status = item.score >= MIN_SCORE ? '✅' : '❌'
              console.log(`    ${status} ${idx + 1}. Score: ${item.score.toFixed(1)} - ${slug}${priceInfo}${variantInfo}`)
            })
            console.log('') // Empty line before debug details

            // Log debug details for all scored links
            allScored.forEach((item) => {
              logDebugDetails(item)
            })
          }

          if (validLinks.length === 0) {
            console.log(`  ⚠️  No relevant products found after filtering (minimum score: ${MIN_SCORE}) - skipping`)
            // Log what was filtered out for debugging
            const allScored = scoredLinks.filter(item => item.productLink).sort((a, b) => b.score - a.score)
            if (allScored.length > 0) {
              const topCount = DEBUG ? allScored.length : Math.min(3, allScored.length)
              console.log(`  Top scored (but below threshold, showing ${topCount}):`)
              allScored.slice(0, topCount).forEach((item, idx) => {
                const slug = item.productLink.url.split('/p/').pop()?.split('?')[0] ?? ''
                console.log(`    ${idx + 1}. Score: ${item.score.toFixed(1)} - ${slug}`)
                // Log debug details for all items in debug mode, or top 3 otherwise
                logDebugDetails(item)
              })
              if (DEBUG && allScored.length > topCount) {
                console.log(`    ... and ${allScored.length - topCount} more URLs (all scored below threshold)`)
              }
            }
            productLinks = []
          } else {
            // Log scoring details
            console.log(`  Scoring results (minimum score: ${MIN_SCORE}):`)
            validLinks.forEach((item, idx) => {
              const slug = item.productLink.url.split('/p/').pop()?.split('?')[0] ?? ''
              const priceInfo = item.productLink.price ? ` (${item.productLink.price} PLN)` : ''
              const variantInfo = item.productLink.variant ? ` [${item.productLink.variant}]` : ''
              console.log(`    ${idx + 1}. Score: ${item.score.toFixed(1)} - ${slug}${priceInfo}${variantInfo}`)
            })

            // Log debug details for all valid links if DEBUG enabled
            if (DEBUG) {
              validLinks.forEach((item) => {
                logDebugDetails(item)
              })
            }

            // Take only the best match (or top 3 if scores are very close)
            const topScore = validLinks[0].score
            const threshold = Math.max(MIN_SCORE, topScore * 0.70) // 70% of top score, but at least MIN_SCORE

            const bestMatches = validLinks.filter(item => item.score >= threshold).slice(0, 3)
            productLinks = bestMatches.map(item => item.productLink).filter((link): link is ProductLink => link !== undefined)

            console.log(`  ✅ Selected ${productLinks.length} best match(es) (score >= ${threshold.toFixed(1)})`)
          }
        }

        if (productLinks.length > 0) {
          console.log(`Found ${productLinks.length} product(s):`)
          productLinks.forEach((productLink, idx) => {
            const priceInfo = productLink.price ? ` (${productLink.price} PLN)` : ''
            const variantInfo = productLink.variant ? ` [${productLink.variant}]` : ''
            console.log(`  ${idx + 1}. ${productLink.url}${priceInfo}${variantInfo}`)
          })

          results.push({
            productId: product.id,
            productName: product.name,
            foundUrls: productLinks
          })
        } else {
          console.log('  No products found')
          results.push({
            productId: product.id,
            productName: product.name,
            foundUrls: []
          })
        }

        // Small delay between searches to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1500))
      } catch (error) {
        console.error(`Error searching for ${product.name}:`, error)
        results.push({
          productId: product.id,
          productName: product.name,
          foundUrls: []
        })
      }
    }

      // Update the JSON file
      console.log('\n\nUpdating catalogue_items.json...')
      updateJsonFile(jsonPath, results)

      const foundCount = results.filter(r => r.foundUrls.length > 0).length
      console.log(`\nCompleted! Found URLs for ${foundCount} out of ${products.length} products`)

      // Close readline interface if it was opened
      if (rl) {
        rl.close()
      }
    } finally {
      // Cleanup: restore console and close log file (always, even on error)
      cleanup()
    }
  })
})


