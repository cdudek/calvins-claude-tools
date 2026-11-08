#!/usr/bin/env bash
# Usage: bash test_assertion_guard.sh
# Proves assertion-guard.sh passes added assertions, fails dropped or parked ones, and lets a
# named drop reason through. Builds a throwaway git repo, so it needs only git.
# Output sections: -#-#- RESULTS -#-#-
set -euo pipefail

GUARD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/assertion-guard.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
git init -q -b main
git config user.email t@t && git config user.name t
mkdir e2e
cat >e2e/a.spec.ts <<'TS'
test('a', async () => {
  await expect(one).toBeVisible()
  await expect.soft(two).toHaveText(x)
})
TS
git add . && git commit -qm base

PASSED=0
check() { # name, expected exit, [env assignment]
  local name="$1" want="$2" got=0
  if [ -n "${3:-}" ]; then env "$3" bash "$GUARD" main >/dev/null 2>&1 || got=$?
  else bash "$GUARD" main >/dev/null 2>&1 || got=$?; fi
  [ "$got" -eq "$want" ] || { echo "- FAIL: $name (exit $got, wanted $want)"; exit 1; }
  echo "- ok: $name"; PASSED=$((PASSED + 1))
}
case_branch() { git checkout -q main && git checkout -q -B "$1"; }

echo "-#-#- RESULTS -#-#-"
case_branch add
perl -pi -e 's/^\}\)$/  await expect(three).toBeChecked()\n})/' e2e/a.spec.ts
git commit -qam add
check "an added assertion passes" 0

case_branch drop
sed -i.bak '/expect.soft/d' e2e/a.spec.ts && rm e2e/a.spec.ts.bak
git commit -qam drop
check "a dropped assertion fails" 1
check "a dropped assertion with a reason passes" 0 "E2E_ASSERTION_DROP_REASON=journey J4 moved to T3"

case_branch park
sed -i.bak "s/^test('a'/test.fixme('a'/" e2e/a.spec.ts && rm e2e/a.spec.ts.bak
git commit -qam park
check "a fixme fails" 1

case_branch reword
sed -i.bak 's/toHaveText(x)/toHaveText(y)/' e2e/a.spec.ts && rm e2e/a.spec.ts.bak
git commit -qam reword
check "a changed assertion is not a drop" 0

case_branch uncommitted
sed -i.bak '/expect.soft/d' e2e/a.spec.ts && rm e2e/a.spec.ts.bak
check "an uncommitted dropped assertion fails" 1
git checkout -q -- e2e/a.spec.ts

printf "test.skip('b', async () => {})\n" >e2e/b.spec.ts
check "a new untracked file that parks a test fails" 1
rm e2e/b.spec.ts

echo "- $PASSED passed"
