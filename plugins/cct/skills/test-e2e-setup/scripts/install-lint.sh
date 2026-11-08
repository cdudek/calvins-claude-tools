#!/usr/bin/env bash
# Usage: bash install-lint.sh <repo-root>
# Installs the e2e lint preset, the copy-catalogue rule, the copy fixture and the
# persona and journey templates and the token helper into a target repo. Never overwrites an existing file.
# Output sections: -#-#- DETECTED -#-#-, -#-#- INSTALLED -#-#-, -#-#- NEXT -#-#-
set -euo pipefail

ROOT="${1:-}"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "usage: bash install-lint.sh <repo-root>" >&2; exit 2; }
ROOT="$(cd "$ROOT" && pwd)"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../templates" && pwd)"

# --- detect the repo's shape so the operator does not have to guess ---------------
echo "-#-#- DETECTED -#-#-"

SPEC_DIR=""
for d in e2e tests/e2e playwright cypress/e2e; do
  [ -d "$ROOT/$d" ] && { SPEC_DIR="$d"; break; }
done
echo "- spec_dir: ${SPEC_DIR:-none found}"

CATALOGUE=""
for c in src/i18n/locales/en.json src/locales/en.json public/locales/en/common.json \
         messages/en.json locales/en.json src/i18n/en.json; do
  [ -f "$ROOT/$c" ] && { CATALOGUE="$c"; break; }
done
echo "- catalogue: ${CATALOGUE:-none found}"

PW_VERSION="$(node -e "try{console.log(require('$ROOT/node_modules/@playwright/test/package.json').version)}catch(e){console.log('not installed')}" 2>/dev/null || echo unknown)"
echo "- playwright: $PW_VERSION"

HAS_LINT_PLUGIN=no
[ -d "$ROOT/node_modules/eslint-plugin-playwright" ] && HAS_LINT_PLUGIN=yes
echo "- eslint-plugin-playwright: $HAS_LINT_PLUGIN"

TARGET="${SPEC_DIR:-e2e}"
mkdir -p "$ROOT/$TARGET/eslint-rules"

# --- copy, never clobber -----------------------------------------------------------
echo "-#-#- INSTALLED -#-#-"
install_one() {
  local src="$1" dst="$2"
  if [ -e "$ROOT/$dst" ]; then
    echo "- skipped (exists): $dst"
  else
    cp "$src" "$ROOT/$dst"
    echo "- wrote: $dst"
  fi
}

install_one "$SRC/eslint.config.e2e.mjs"            "$TARGET/eslint.config.e2e.mjs"
install_one "$SRC/eslint-rules/no-catalogue-copy.js" "$TARGET/eslint-rules/no-catalogue-copy.js"
install_one "$SRC/personas.md"                       "$TARGET/personas.md"
install_one "$SRC/journeys.md"                       "$TARGET/journeys.md"
install_one "$SRC/tokens.ts"                         "$TARGET/tokens.ts"
[ -n "$CATALOGUE" ] && install_one "$SRC/i18n-fixture.ts" "$TARGET/i18n.ts"

# --- what the operator still has to do ---------------------------------------------
echo "-#-#- NEXT -#-#-"
[ "$HAS_LINT_PLUGIN" = no ] && echo "- install the plugin: pnpm add -D eslint-plugin-playwright"
[ -z "$CATALOGUE" ] && echo "- no copy catalogue found: set CATALOGUES in $TARGET/eslint.config.e2e.mjs, or leave it empty if the product is single-locale"
[ -n "$CATALOGUE" ] && echo "- point CATALOGUES at '$CATALOGUE' in $TARGET/eslint.config.e2e.mjs and fix the imports in $TARGET/i18n.ts"
echo "- set FILES in $TARGET/eslint.config.e2e.mjs to this repo's spec glob"
echo "- merge the preset into eslint.config.mjs: import e2e from './$TARGET/eslint.config.e2e.mjs'"
echo "- fill in $TARGET/personas.md — the planner reads it"
echo "- fill in $TARGET/journeys.md: journeys, tiers, owners, budget (cct:test-e2e-policy, references/strategy.md section 2)"
echo "- gate PRs on scripts/assertion-guard.sh <base-ref> $TARGET"
echo "- expect failures on the existing suite: fix by rule, one rule per PR, not all at once"
