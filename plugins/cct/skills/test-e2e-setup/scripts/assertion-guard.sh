#!/usr/bin/env bash
# Usage: bash assertion-guard.sh <base-ref> [spec-dir]
# Fails when the change since <base-ref> removes more expect() calls than it adds in
# spec-dir (default: e2e), or adds .skip / .fixme / .only. "The change" is everything not in
# the base: commits, uncommitted edits and new untracked files, so a healer that has not
# committed yet is checked too. Deleting obsolete coverage is
# legitimate: set E2E_ASSERTION_DROP_REASON="<why>" and the drop passes, printed for review.
# Run from the repo root. Output sections: -#-#- RESULTS -#-#-
set -euo pipefail

BASE="${1:-}"
DIR="${2:-e2e}"
[ -n "$BASE" ] || { echo "usage: bash assertion-guard.sh <base-ref> [spec-dir]" >&2; exit 2; }

# Against the merge base, into the working tree: commits plus uncommitted edits.
DIFF="$(git diff --unified=0 "$(git merge-base "$BASE" HEAD)" -- "$DIR")"
# New untracked files count as added lines.
while IFS= read -r f; do
  [ -n "$f" ] && DIFF="$DIFF"$'\n'"$(sed 's/^/+/' "$f")"
done < <(git ls-files --others --exclude-standard -- "$DIR")
added() { printf '%s\n' "$DIFF" | grep -E '^\+[^+]' | grep -cE "$1" || true; }
removed() { printf '%s\n' "$DIFF" | grep -E '^-[^-]' | grep -cE "$1" || true; }

EXPECT='expect(\.soft|\.poll)?\('
PARKED='\.(skip|fixme|only)\('
ADDED_EXPECT="$(added "$EXPECT")"
REMOVED_EXPECT="$(removed "$EXPECT")"
ADDED_PARKED="$(added "$PARKED")"

echo "-#-#- RESULTS -#-#-"
echo "- expect() added: $ADDED_EXPECT, removed: $REMOVED_EXPECT"
echo "- skip/fixme/only added: $ADDED_PARKED"

FAIL=0
if [ "$ADDED_PARKED" -gt 0 ]; then
  echo "- FAIL: a test was parked. Quarantine is a person's decision, recorded in e2e/journeys.md"
  printf '%s\n' "$DIFF" | grep -E '^\+[^+]' | grep -E "$PARKED" | sed 's/^/    /'
  FAIL=1
fi
if [ "$REMOVED_EXPECT" -gt "$ADDED_EXPECT" ]; then
  if [ -n "${E2E_ASSERTION_DROP_REASON:-}" ]; then
    echo "- PASS WITH REASON: net $((REMOVED_EXPECT - ADDED_EXPECT)) assertion(s) dropped: $E2E_ASSERTION_DROP_REASON"
  else
    echo "- FAIL: net $((REMOVED_EXPECT - ADDED_EXPECT)) assertion(s) dropped. If this deletes obsolete coverage, set E2E_ASSERTION_DROP_REASON"
    FAIL=1
  fi
fi
[ "$FAIL" -eq 0 ] && echo "- ok"
exit "$FAIL"
