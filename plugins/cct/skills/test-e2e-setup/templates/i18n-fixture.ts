/**
 * Copy resolution for e2e specs. Enforces § 2 of the locator policy: a spec never
 * contains a user-visible string, it resolves one from the catalogue the application reads.
 *
 * Copy this to `e2e/i18n.ts` and point CATALOGUES at the real files. Nothing below is
 * framework-specific — any JSON catalogue with string leaves works (next-intl, i18next,
 * vue-i18n, react-intl, or a plain copy file).
 *
 *   import { t } from './i18n'
 *   await page.getByRole('button', { name: t('settings.save') }).click()
 *   await expect(page.getByTestId('toast')).toHaveText(t('settings.saved'))
 *
 * Running one spec in every locale:
 *
 *   for (const locale of ['en', 'de']) {
 *     test(`saves settings (${locale})`, async ({ page }) => {
 *       await page.goto(`/${locale}/settings`)
 *       await page.getByRole('button', { name: t('settings.save', { locale }) }).click()
 *     })
 *   }
 */

// Adjust to the project's catalogue layout. The default locale is listed first.
import en from '../src/i18n/locales/en.json' with { type: 'json' }
import de from '../src/i18n/locales/de.json' with { type: 'json' }

const CATALOGUES: Record<string, unknown> = { en, de }
const DEFAULT_LOCALE = 'en'

type Values = Record<string, string | number>

export type TOptions = {
  /** Which locale to resolve in. Defaults to DEFAULT_LOCALE. */
  locale?: string
  /** ICU-style placeholder values: t('greet', { values: { name: 'Ada' } }). */
  values?: Values
}

function lookup(catalogue: unknown, key: string): string | undefined {
  let node: unknown = catalogue
  for (const part of key.split('.')) {
    if (node === null || typeof node !== 'object') return undefined
    node = (node as Record<string, unknown>)[part]
  }
  return typeof node === 'string' ? node : undefined
}

function interpolate(template: string, values: Values): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    if (!(name in values)) {
      throw new Error(
        `e2e/i18n: "${template}" needs a value for {${name}}. Pass it: t(key, { values: { ${name}: … } })`,
      )
    }
    return String(values[name])
  })
}

/**
 * Resolve a copy key to the string the user actually sees.
 *
 * Throws on a missing key and on a missing placeholder value. That is the point: a renamed
 * or deleted key must fail at this line with the key in the message, not silently match
 * nothing and surface as a locator timeout ten seconds later in a different file.
 */
export function t(key: string, options: TOptions = {}): string {
  const locale = options.locale ?? DEFAULT_LOCALE
  const catalogue = CATALOGUES[locale]
  if (!catalogue) {
    throw new Error(
      `e2e/i18n: no catalogue for locale "${locale}". Known: ${Object.keys(CATALOGUES).join(', ')}`,
    )
  }

  const value = lookup(catalogue, key)
  if (value === undefined) {
    throw new Error(`e2e/i18n: missing key "${key}" in locale "${locale}".`)
  }

  return options.values ? interpolate(value, options.values) : value
}

/** Every locale the suite can run against, for parameterised specs. */
export const locales = Object.keys(CATALOGUES)
