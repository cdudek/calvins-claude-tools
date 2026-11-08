#!/usr/bin/env bash
# Usage: review-pending.sh <owner> <repo> <pr_number>
# Detects a PENDING review owned by the current GitHub user on the given PR.
#
# Output (stdout):
# - empty if no pending review
# - JSON object otherwise:
#   {"id": <numeric>, "node_id": "PRR_...", "comment_count": <int>, "current_user": "<login>"}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number>" >&2
  exit 2
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"

if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "Error: pr_number must be a positive integer (got: $PR_NUMBER)" >&2
  exit 2
fi

GH_USER=$(gh api user -q .login)

PENDING=$(gh api "repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/reviews" \
  | jq --arg u "$GH_USER" '[.[] | select(.state == "PENDING" and .user.login == $u)] | first // empty')

if [[ -z "$PENDING" ]]; then
  exit 0
fi

REVIEW_ID=$(echo "$PENDING" | jq -r '.id')
NODE_ID=$(echo "$PENDING" | jq -r '.node_id')
COMMENT_COUNT=$(gh api "repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/reviews/${REVIEW_ID}/comments" --jq 'length')

jq -nc \
  --argjson id "$REVIEW_ID" \
  --arg node_id "$NODE_ID" \
  --argjson comment_count "$COMMENT_COUNT" \
  --arg current_user "$GH_USER" \
  '{id: $id, node_id: $node_id, comment_count: $comment_count, current_user: $current_user}'
