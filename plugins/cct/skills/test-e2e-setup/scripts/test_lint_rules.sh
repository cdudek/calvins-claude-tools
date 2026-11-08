#!/usr/bin/env bash
# Usage: bash test_lint_rules.sh
# Proves the preset pins the web-first wait and assertion rules to error, and, when
# eslint-plugin-playwright is installed, that a spec with waitForTimeout fails the lint.
# Output sections: -#-#- RESULTS -#-#-
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$DIR/../templates/eslint.config.e2e.mjs"
failed=0

echo "-#-#- RESULTS -#-#-"
for r in no-wait-for-timeout no-networkidle prefer-web-first-assertions \
         no-conditional-in-test expect-expect missing-playwright-await; do
  if grep -Eq "'playwright/$r': 'error'" "$CFG"; then echo "PASS  $r is error"
  else echo "FAIL  $r is not pinned to error"; failed=1; fi
done

if [ -n "${PW_LINT_DIR:-}" ] && [ -d "$PW_LINT_DIR/node_modules/eslint-plugin-playwright" ]; then
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  mkdir -p "$TMP/e2e/eslint-rules"
  cp "$CFG" "$TMP/e2e/eslint.config.e2e.mjs"
  cp "$DIR/../templates/eslint-rules/no-catalogue-copy.js" "$TMP/e2e/eslint-rules/"
  ln -s "$PW_LINT_DIR/node_modules" "$TMP/node_modules"
  echo "import e2e from './e2e/eslint.config.e2e.mjs'; export default e2e" >"$TMP/eslint.config.mjs"
  cat >"$TMP/e2e/bad.spec.ts" <<'SPEC'
import { test, expect } from '@playwright/test'
test('x', async ({ page }) => {
  await page.waitForTimeout(500)
  expect(await page.getByRole('button').isVisible()).toBe(true)
})
SPEC
  out="$(cd "$TMP" && "$PW_LINT_DIR/node_modules/.bin/eslint" e2e/bad.spec.ts 2>&1 || true)"
  for r in no-wait-for-timeout prefer-web-first-assertions; do
    if echo "$out" | grep -q "playwright/$r"; then echo "PASS  eslint flags $r"
    else echo "FAIL  eslint did not flag $r"; failed=1; fi
  done
else
  echo "SKIP  eslint run (set PW_LINT_DIR to a dir with eslint + eslint-plugin-playwright)"
fi
exit $failed
