// e2e lint preset — enforces plugins/cct/skills/test-e2e-policy/references/locator-policy.md
//
// Usage: merge into the repo's eslint.config.mjs
//
//   import e2e from './e2e/eslint.config.e2e.mjs'
//   export default [ ...existing, ...e2e ]
//
// Adjust FILES to the repo's spec glob and CATALOGUES to its copy catalogue(s).
// Everything else is policy and should not be edited per repo — if a rule does not fit,
// that is a finding about the rule, not a reason to drop it locally.

import playwright from 'eslint-plugin-playwright'
import noCatalogueCopy from './eslint-rules/no-catalogue-copy.js'

/** Spec files this preset governs. */
const FILES = ['e2e/**/*.ts', 'e2e/**/*.tsx', 'tests/e2e/**/*.ts']

/**
 * Copy catalogues, relative to the repo root. The custom rule loads these and fails any
 * spec literal that matches a value in them.
 *
 * next-intl / react-intl:  ['src/i18n/locales/en.json']
 * i18next:                 ['public/locales/en/common.json', ...]
 * vue-i18n:                ['src/locales/en.json']
 * no catalogue:            []  — the rule then does nothing, which is correct
 */
const CATALOGUES = ['src/i18n/locales/en.json']

/**
 * Elements with no ARIA role that a raw locator may legitimately reach.
 * Keep this list short and justify every addition in a comment.
 */
const RAW_LOCATOR_ALLOWLIST = ['iframe']

export default [
  {
    ...playwright.configs['flat/recommended'],
    files: FILES,
  },
  {
    files: FILES,
    // playwright is already registered by flat/recommended above; redefining it throws.
    plugins: { e2e: { rules: { 'no-catalogue-copy': noCatalogueCopy } } },
    rules: {
      // --- locator-policy.md § 5: raw CSS and XPath are banned -----------------
      'playwright/no-raw-locators': ['error', { allowed: RAW_LOCATOR_ALLOWLIST }],
      'playwright/prefer-native-locators': 'error',
      'playwright/no-get-by-title': 'error',

      // --- locator-policy.md § 3: positional selection is a missing test id ----
      'playwright/no-nth-methods': 'error',

      // --- waiting.md § 10: banned waits ----------------------------------------
      // The preset's flat/recommended leaves no-wait-for-timeout, no-conditional-in-test and
      // expect-expect at warn, so all six are pinned to error here.
      'playwright/no-wait-for-timeout': 'error',
      'playwright/no-networkidle': 'error',
      'playwright/prefer-web-first-assertions': 'error',
      'playwright/no-conditional-in-test': 'error',
      'playwright/missing-playwright-await': 'error',
      // A test with no assertion proves nothing. A repo whose helpers assert (for example
      // expectToast) extends the list: ['error', { assertFunctionNames: ['expectToast'] }]
      'playwright/expect-expect': 'error',
      'playwright/no-force-option': 'error',
      'playwright/no-wait-for-selector': 'error',
      'playwright/no-action-timeout': 'error',
      'playwright/no-magic-timeouts': ['warn', { minOccurrences: 2 }],
      'playwright/require-to-pass-timeout': 'error',

      // --- locator-policy.md § 2: never write a user-visible string in a spec ---
      'e2e/no-catalogue-copy': ['error', { catalogues: CATALOGUES }],

      // --- the policy hook -----------------------------------------------------
      // Empty by default. Add an entry here when a locator becomes house-banned,
      // with the message pointing at the replacement — never a bare ban.
      'playwright/no-restricted-locators': ['error', []],
    },
  },
]
