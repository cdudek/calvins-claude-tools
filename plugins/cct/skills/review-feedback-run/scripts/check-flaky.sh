#!/usr/bin/env bash
# Check if a failed CI check also fails on the base branch.
# Usage: check-flaky.sh <base_branch> <check_name> [repo]
# Output: "FLAKY" if also fails on base, "NOT_FLAKY" otherwise, "NO_DATA" if check not found
#
# The check_name must match the GitHub check/job name (e.g., "lint", "test", "build"),
# NOT the workflow name. Use `gh pr checks <PR>` to see correct check names.
set -euo pipefail

BASE="${1:?Usage: check-flaky.sh <base_branch> <check_name> [repo]}"
CHECK_NAME="${2:?Usage: check-flaky.sh <base_branch> <check_name> [repo]}"
if [ -n "${3:-}" ]; then
  REPO="$3"
else
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || {
    echo "NO_DATA"
    exit 0
  }
fi

COMMITS_TO_CHECK=10
FOUND=0
FAILED=0

# Get recent commit SHAs on the base branch
SHAS=$(gh api "repos/$REPO/commits" -F sha="$BASE" -F per_page="$COMMITS_TO_CHECK" --jq '.[].sha' 2>/dev/null) || {
  echo "NO_DATA"
  exit 0
}

if [ -z "$SHAS" ]; then
  echo "NO_DATA"
  exit 0
fi

# Check each commit for the specific check/job by name
while IFS= read -r sha; do
  [ -z "$sha" ] && continue
  RESULT=$(gh api "repos/$REPO/commits/$sha/check-runs" -F check_name="$CHECK_NAME" \
    --jq '.check_runs[0] | if . == null then "not_found" elif .status != "completed" then "pending" else .conclusion end' 2>/dev/null) || continue

  case "$RESULT" in
    not_found|null|"") continue ;;
    pending) continue ;;
    failure|timed_out|cancelled|action_required|startup_failure)
      FOUND=$((FOUND + 1))
      FAILED=$((FAILED + 1))
      ;;
    *)
      FOUND=$((FOUND + 1))
      ;;
  esac
done <<< "$SHAS"

if [ "$FOUND" -eq 0 ]; then
  echo "NO_DATA"
elif [ "$FOUND" -le 2 ] && [ "$FAILED" -lt "$FOUND" ]; then
  # Sparse data with partial failures — could be one-off infra issue, not enough signal
  echo "NO_DATA"
elif [ "$FAILED" -ge 2 ] || [ "$(( FAILED * 100 / FOUND ))" -ge 50 ]; then
  # Flaky if 2+ failures or majority of runs fail
  echo "FLAKY"
else
  echo "NOT_FLAKY"
fi
