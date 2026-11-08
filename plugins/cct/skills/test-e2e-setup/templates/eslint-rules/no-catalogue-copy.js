/**
 * e2e/no-catalogue-copy — a spec may not hardcode a string that lives in a copy catalogue.
 *
 * Enforces § 2 of the locator policy. Loads the project's own catalogue at rule-init,
 * builds a value -> key map, and reports any string literal handed to a locator or a text
 * assertion that matches a catalogue value.
 *
 * Catalogue-format agnostic: any JSON file whose leaves are strings. Nested objects are
 * flattened with dots, so next-intl, i18next, vue-i18n and a plain copy file all work.
 *
 * Options:
 *   catalogues  string[]  paths relative to cwd. No catalogue -> the rule does nothing.
 *   minLength   number    ignore values shorter than this (default 4). Stops "OK" / "Save"
 *                         from flagging every unrelated literal that happens to match.
 *   allow       string[]  exact values that may be inlined anyway.
 *   matchers    string[]  callee/property names whose string arguments are checked.
 *
 * Why value -> key and not key -> value: the defect is a spec that typed the rendered
 * English by hand. Only the rendered value is present to match against.
 */

import fs from 'node:fs'
import path from 'node:path'

const DEFAULT_MATCHERS = [
  'getByText',
  'getByLabel',
  'getByPlaceholder',
  'getByTitle',
  'getByAltText',
  'toHaveText',
  'toContainText',
  'toHaveTitle',
  'toHaveLabel',
  'toHaveAccessibleName',
  'toHaveValue',
]

/** Flatten a nested catalogue into dotted key -> string value. */
function flatten(node, prefix, out) {
  for (const [k, v] of Object.entries(node)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (typeof v === 'string') out.set(v, key)
    else if (v && typeof v === 'object') flatten(v, key, out)
  }
  return out
}

/** value -> key, for every catalogue that exists. A missing file is not an error: a repo
 *  may legitimately have none, and failing lint over it would punish the wrong person. */
function loadCatalogues(catalogues, cwd) {
  const map = new Map()
  for (const rel of catalogues) {
    const abs = path.resolve(cwd, rel)
    if (!fs.existsSync(abs)) continue
    try {
      flatten(JSON.parse(fs.readFileSync(abs, 'utf8')), '', map)
    } catch {
      // A malformed catalogue is the app's problem and its own build will say so.
      continue
    }
  }
  return map
}

/** ICU/interpolation placeholders never survive into a spec literal verbatim. */
const hasPlaceholder = (s) => /\{[^}]+\}/.test(s)

const rule = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'disallow hardcoding a string that lives in a copy catalogue; resolve it through the catalogue instead',
    },
    schema: [
      {
        type: 'object',
        properties: {
          catalogues: { type: 'array', items: { type: 'string' } },
          minLength: { type: 'number' },
          allow: { type: 'array', items: { type: 'string' } },
          matchers: { type: 'array', items: { type: 'string' } },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      hardcoded:
        'This string is "{{key}}" in the copy catalogue. Resolve it — t(\'{{key}}\') — so a copy edit does not break the test. See the locator policy § 2.',
    },
  },

  create(context) {
    const opts = context.options[0] ?? {}
    const catalogues = opts.catalogues ?? []
    if (catalogues.length === 0) return {}

    const minLength = opts.minLength ?? 4
    const allow = new Set(opts.allow ?? [])
    const matchers = new Set(opts.matchers ?? DEFAULT_MATCHERS)
    const cwd = context.cwd ?? process.cwd()
    const byValue = loadCatalogues(catalogues, cwd)
    if (byValue.size === 0) return {}

    function check(node) {
      if (node?.type !== 'Literal' || typeof node.value !== 'string') return
      const value = node.value
      if (value.length < minLength || allow.has(value) || hasPlaceholder(value)) return
      const key = byValue.get(value)
      if (key) context.report({ node, messageId: 'hardcoded', data: { key } })
    }

    /** `name:` inside getByRole(...) / getByLabel(...) options is copy too. */
    function checkNameOption(arg) {
      if (arg?.type !== 'ObjectExpression') return
      for (const prop of arg.properties) {
        if (prop.type !== 'Property') continue
        const n = prop.key?.name ?? prop.key?.value
        if (n === 'name' || n === 'hasText') check(prop.value)
      }
    }

    return {
      CallExpression(node) {
        const callee = node.callee
        const name = callee?.type === 'MemberExpression' ? callee.property?.name : callee?.name
        if (!name) return

        if (matchers.has(name)) {
          node.arguments.forEach(check)
          return
        }
        // getByRole('button', { name: '...' }) and .filter({ hasText: '...' })
        if (name === 'getByRole' || name === 'filter') {
          node.arguments.forEach(checkNameOption)
        }
      },
    }
  },
}

export default rule
