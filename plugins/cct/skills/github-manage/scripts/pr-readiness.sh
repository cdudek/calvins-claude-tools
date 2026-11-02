#!/usr/bin/env bash
# Usage: pr-readiness.sh <pr_number>
# Informational mergeability state. Does NOT gate any action — display only.
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- MERGEABLE -#-#-     (key-value: is_draft, state, mergeable, merge_state)
#   -#-#- CHECKS -#-#-         (key-value summary: total, passing, failing, pending)
#   -#-#- CHECKS_FAILING -#-#-  (only when checks failing; per-check name list)
#   -#-#- CHECKS_PENDING -#-#-  (only when checks pending; per-check name list)
#   -#-#- STALENESS -#-#-     (ahead/behind base — from GitHub's mergeStateStatus)
#   -#-#- REVIEW_DECISION -#-#- (key-value: review decision)
#   -#-#- READY -#-#-         (key-value: ready_to_merge bool, blockers list)
set -euo pipefail

PR="${1:?Usage: pr-readiness.sh <pr_number>}"

DATA=$(gh pr view "$PR" --json isDraft,state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup)

IS_DRAFT=$(echo "$DATA" | jq -r '.isDraft')
STATE=$(echo "$DATA" | jq -r '.state')
MERGEABLE=$(echo "$DATA" | jq -r '.mergeable')
MERGE_STATE=$(echo "$DATA" | jq -r '.mergeStateStatus')
REVIEW=$(echo "$DATA" | jq -r '.reviewDecision // "NONE"')

echo "-#-#- MERGEABLE -#-#-"
echo "- is_draft: $IS_DRAFT"
echo "- state: $STATE"
echo "- mergeable: $MERGEABLE"
echo "- merge_state: $MERGE_STATE"

echo ""
echo "-#-#- CHECKS -#-#-"
TOTAL=$(echo "$DATA" | jq -r '(.statusCheckRollup // []) | length')
PASSING=$(echo "$DATA" | jq -r '[(.statusCheckRollup // [])[] | select(.conclusion == "SUCCESS" or .state == "SUCCESS")] | length')
FAILING=$(echo "$DATA" | jq -r '[(.statusCheckRollup // [])[] | select(.conclusion == "FAILURE" or .state == "FAILURE" or .conclusion == "TIMED_OUT" or .conclusion == "CANCELLED")] | length')
PENDING=$(echo "$DATA" | jq -r '[(.statusCheckRollup // [])[] | select(.status == "IN_PROGRESS" or .status == "QUEUED" or .state == "PENDING")] | length')
echo "- total: $TOTAL"
echo "- passing: $PASSING"
echo "- failing: $FAILING"
echo "- pending: $PENDING"
if [ "$FAILING" -gt 0 ]; then
  echo ""
  echo "-#-#- CHECKS_FAILING -#-#-"
  echo "$DATA" | jq -r '(.statusCheckRollup // [])[] | select(.conclusion == "FAILURE" or .state == "FAILURE" or .conclusion == "TIMED_OUT" or .conclusion == "CANCELLED") | "- \(.name // .context): \(.conclusion // .state)"'
fi
if [ "$PENDING" -gt 0 ]; then
  echo ""
  echo "-#-#- CHECKS_PENDING -#-#-"
  echo "$DATA" | jq -r '(.statusCheckRollup // [])[] | select(.status == "IN_PROGRESS" or .status == "QUEUED" or .state == "PENDING") | "- \(.name // .context)"'
fi

echo ""
echo "-#-#- STALENESS -#-#-"
# Staleness comes from GitHub's mergeStateStatus — BEHIND means the head ref
# is behind base. We don't fetch locally because it adds latency, fails on
# worktrees that don't track the head ref, and the local ahead/behind numbers
# are misleading when the fetch fails.
case "$MERGE_STATE" in
  BEHIND) echo "- behind_base: true" ;;
  *)      echo "- behind_base: false" ;;
esac

echo ""
echo "-#-#- REVIEW_DECISION -#-#-"
echo "- decision: $REVIEW"

echo ""
echo "-#-#- READY -#-#-"
BLOCKERS=()
[ "$IS_DRAFT" = "true" ] && BLOCKERS+=("is_draft")
[ "$STATE" != "OPEN" ] && BLOCKERS+=("not_open")
[ "$MERGEABLE" = "CONFLICTING" ] && BLOCKERS+=("conflicts")
[ "$FAILING" -gt 0 ] && BLOCKERS+=("checks_failing")
[ "$PENDING" -gt 0 ] && BLOCKERS+=("checks_pending")
[ "$REVIEW" = "REVIEW_REQUIRED" ] && BLOCKERS+=("reviews_required")
[ "$REVIEW" = "CHANGES_REQUESTED" ] && BLOCKERS+=("changes_requested")
[ "$MERGE_STATE" = "BEHIND" ] && BLOCKERS+=("behind_base")
[ "$MERGE_STATE" = "BLOCKED" ] && BLOCKERS+=("blocked")
[ "$MERGE_STATE" = "DIRTY" ] && BLOCKERS+=("dirty")
[ "$MERGE_STATE" = "UNSTABLE" ] && BLOCKERS+=("unstable")
if [ ${#BLOCKERS[@]} -eq 0 ]; then
  echo "- ready_to_merge: true"
  echo "- blockers: none"
else
  echo "- ready_to_merge: false"
  echo "- blockers: $(IFS=,; echo "${BLOCKERS[*]}")"
fi
