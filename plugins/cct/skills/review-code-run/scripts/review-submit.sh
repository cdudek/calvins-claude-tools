#!/usr/bin/env bash
# Usage: cat summary.md | review-submit.sh <review_node_id> <event>
# Submits a pending review with the given summary and event.
# event: COMMENT | APPROVE | REQUEST_CHANGES (DISMISS is intentionally unsupported here)
#
# The script appends "🤖 Co-reviewed with Claude Code" to the body.
#
# Output: {"state": "COMMENTED|APPROVED|CHANGES_REQUESTED"}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <review_node_id> <event>" >&2
  echo "  Summary read from stdin." >&2
  exit 2
fi

REVIEW_NODE_ID="$1"
EVENT="$2"
BODY=$(cat)

case "$EVENT" in
  COMMENT|APPROVE|REQUEST_CHANGES) ;;
  *)
    echo "Error: event must be one of COMMENT, APPROVE, REQUEST_CHANGES (got: $EVENT)" >&2
    exit 2
    ;;
esac

FULL_BODY="${BODY}

🤖 Co-reviewed with Claude Code"

QUERY='mutation($review: ID!, $event: PullRequestReviewEvent!, $body: String!) {
  submitPullRequestReview(input: {
    pullRequestReviewId: $review,
    event: $event,
    body: $body
  }) {
    pullRequestReview { state }
  }
}'

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --arg review "$REVIEW_NODE_ID" \
  --arg event "$EVENT" \
  --arg body "$FULL_BODY" \
  '{query: $query, variables: {review: $review, event: $event, body: $body}}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

STATE=$(echo "$RESPONSE" | jq -r '.data.submitPullRequestReview.pullRequestReview.state // empty')

if [[ -z "$STATE" ]]; then
  echo "Error: submitPullRequestReview failed" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc --arg state "$STATE" '{state: $state}'
