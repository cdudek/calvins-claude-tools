#!/usr/bin/env bash
# Usage: bash test_no_catalogue_copy.sh
# Proves the no-catalogue-copy ESLint rule flags hardcoded catalogue copy and nothing else.
# Runs the rule against hand-built AST nodes — no eslint install needed, so CI stays cheap.
# Output sections: -#-#- RESULTS -#-#-
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE="$DIR/../templates/eslint-rules/no-catalogue-copy.js"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat >"$TMP/en.json" <<'JSON'
{
  "settings": { "save": "Save changes", "saved": "Your settings were saved." },
  "short": "OK",
  "greet": "Hello {name}"
}
JSON

cp "$RULE" "$TMP/rule.mjs"

cat >"$TMP/check.mjs" <<'NODE'
import rule from './rule.mjs'

const lit = (value) => ({ type: 'Literal', value })
const prop = (name, value) => ({ type: 'Property', key: { name }, value: lit(value) })
const call = (name, args) => ({
  type: 'CallExpression',
  callee: { type: 'MemberExpression', property: { name } },
  arguments: args,
})

function run(node, options) {
  const reports = []
  const ctx = {
    options: [options],
    cwd: process.cwd(),
    report: (r) => reports.push(r.data.key),
  }
  const visitor = rule.create(ctx)
  if (visitor.CallExpression) visitor.CallExpression(node)
  return reports
}

const opts = { catalogues: ['en.json'] }
let failed = 0
const check = (label, actual, expected) => {
  const ok = JSON.stringify(actual) === JSON.stringify(expected)
  if (!ok) failed++
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${ok ? '' : ` — got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`}`)
}

check('getByText on catalogue copy is flagged',
  run(call('getByText', [lit('Save changes')]), opts), ['settings.save'])

check('nested key resolves to its dotted path',
  run(call('toContainText', [lit('Your settings were saved.')]), opts), ['settings.saved'])

check('getByRole name option is checked',
  run(call('getByRole', [lit('button'), { type: 'ObjectExpression', properties: [prop('name', 'Save changes')] }]), opts),
  ['settings.save'])

check('filter hasText is checked',
  run(call('filter', [{ type: 'ObjectExpression', properties: [prop('hasText', 'Save changes')] }]), opts),
  ['settings.save'])

check('a string absent from the catalogue is not flagged',
  run(call('getByText', [lit('Not in the catalogue')]), opts), [])

check('short values are below the length floor',
  run(call('getByText', [lit('OK')]), opts), [])

check('an interpolated value is never matched verbatim',
  run(call('getByText', [lit('Hello {name}')]), opts), [])

check('the allow list wins',
  run(call('getByText', [lit('Save changes')]), { ...opts, allow: ['Save changes'] }), [])

check('no catalogue configured means the rule is inert',
  run(call('getByText', [lit('Save changes')]), { catalogues: [] }), [])

check('a missing catalogue file is not an error',
  run(call('getByText', [lit('Save changes')]), { catalogues: ['nope.json'] }), [])

check('a non-matcher call is ignored',
  run(call('click', [lit('Save changes')]), opts), [])

process.exit(failed === 0 ? 0 : 1)
NODE

echo "-#-#- RESULTS -#-#-"
cd "$TMP" && node check.mjs
