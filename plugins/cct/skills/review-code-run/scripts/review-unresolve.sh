#!/usr/bin/env bash
# Usage: review-unresolve.sh <thread_node_id>
# Unresolves a resolved review thread. Takes effect immediately (not part of pending review).
# Call AFTER submitPullRequestReview so the reply is visible before the thread is unresolved.
#
# Output: {"thread_id": "PRRT_...", "is_resolved": false}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <thread_node_id>" >&2
  exit 2
fi

THREAD_NODE_ID="$1"

QUERY='mutation($thread: ID!) {
  unresolveReviewThread(input: {threadId: $thread}) {
    thread { id isResolved }
  }
}'

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --arg thread "$THREAD_NODE_ID" \
  '{query: $query, variables: {thread: $thread}}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

THREAD_ID=$(echo "$RESPONSE" | jq -r '.data.unresolveReviewThread.thread.id // empty')
IS_RESOLVED=$(echo "$RESPONSE" | jq -r '.data.unresolveReviewThread.thread.isResolved')

if [[ -z "$THREAD_ID" ]]; then
  echo "Error: unresolveReviewThread failed" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc \
  --arg id "$THREAD_ID" \
  --argjson resolved "$IS_RESOLVED" \
  '{thread_id: $id, is_resolved: $resolved}'
