#!/usr/bin/env bash
# Usage: review-create-pending.sh <pr_node_id>
# Creates an empty pending review (no event = PENDING state).
# Used in Scenario A when there are no `new`-action findings (only replies/reopens).
#
# Output: {"node_id": "PRR_..."}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <pr_node_id>" >&2
  exit 2
fi

PR_NODE_ID="$1"

QUERY='mutation($pr: ID!) {
  addPullRequestReview(input: {pullRequestId: $pr}) {
    pullRequestReview { id }
  }
}'

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --arg pr "$PR_NODE_ID" \
  '{query: $query, variables: {pr: $pr}}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

NODE_ID=$(echo "$RESPONSE" | jq -r '.data.addPullRequestReview.pullRequestReview.id // empty')

if [[ -z "$NODE_ID" ]]; then
  echo "Error: addPullRequestReview returned null pullRequestReview" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc --arg node_id "$NODE_ID" '{node_id: $node_id}'
