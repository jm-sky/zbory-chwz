# FEATURE-001: Browser Locale Detection

**Status:** ✅ Completed  
**Priority:** Medium  
**Category:** 🌐 Internationalization  
**Related:** ROADMAP.md - Internacjonalizacja

---

## 📋 Overview

Automatic detection of user's language preference from browser settings with fallback to default language and manual override option.

---

## 🎯 Goals

- Automatically detect user's browser language on first visit
- Fallback to default language (Polish) if browser language is not supported
- Allow manual language change in settings
- Persist language preference in localStorage

---

## 🔍 Current State

- i18n is already configured with `vue-i18n`
- Locale persistence in localStorage exists (`LOCALE_STORAGE_KEY`)
- `useLocale()` composable exists for locale management
- Supported locales: `en`, `pl`
- Default locale is loaded from localStorage or falls back to config

**What's missing:**
- Initial browser language detection on first visit
- Automatic detection when localStorage is empty

---

## 📝 Implementation Plan

### Step 1: Enhance Locale Detection

**File:** `src/shared/i18n/config/i18n.ts`

Update `getStoredLocale()` function to:
1. Check localStorage first (existing behavior)
2. If not found, detect browser language using `navigator.language` or `navigator.languages`
3. Match browser language to supported locales
4. Fallback to config default if no match

```typescript
const getBrowserLocale = (): SupportedLocale | null => {
  // Try navigator.language first
  const browserLang = navigator.language.split('-')[0] // e.g., 'en-US' -> 'en'
  
  if (SUPPORTED_LOCALES.includes(browserLang as SupportedLocale)) {
    return browserLang as SupportedLocale
  }
  
  // Try navigator.languages array
  for (const lang of navigator.languages) {
    const langCode = lang.split('-')[0]
    if (SUPPORTED_LOCALES.includes(langCode as SupportedLocale)) {
      return langCode as SupportedLocale
    }
  }
  
  return null
}

const getStoredLocale = (): SupportedLocale => {
  // Check localStorage first
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale
  }
  
  // Detect from browser
  const browserLocale = getBrowserLocale()
  if (browserLocale) {
    // Save detected locale to localStorage
    localStorage.setItem(LOCALE_STORAGE_KEY, browserLocale)
    return browserLocale
  }
  
  // Fallback to config default
  return config.i18n.fallbackLocale
}
```

### Step 2: Update HTML lang Attribute

**File:** `src/main.ts` or `src/App.vue`

Ensure HTML lang attribute is set on app initialization:

```typescript
// In main.ts after i18n setup
document.documentElement.setAttribute('lang', i18n.global.locale.value)
```

### Step 3: Testing

- Test with different browser language settings
- Test fallback behavior
- Test localStorage persistence
- Test manual locale switching

---

## 📁 Files to Modify

- `src/shared/i18n/config/i18n.ts` - Enhance locale detection
- `src/main.ts` - Ensure HTML lang attribute is set

---

## ✅ Acceptance Criteria

- [ ] Browser language is automatically detected on first visit
- [ ] Detected language is saved to localStorage
- [ ] Fallback to default (Polish) works when browser language is unsupported
- [ ] Manual language switching still works
- [ ] HTML lang attribute is correctly set
- [ ] Works across different browsers (Chrome, Firefox, Safari, Edge)

---

## 🔗 Related Features

- Settings page for manual locale selection (if not exists)

