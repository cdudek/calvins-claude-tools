#!/usr/bin/env bash
# Mark a PR review thread as resolved via GitHub GraphQL.
# Usage: resolve-thread.sh <thread_id>
#   thread_id: GraphQL node ID from gather-pr-feedback.sh REVIEW_THREADS section
# Output: -#-#- RESULT -#-#- with thread_id and isResolved (true/false)
set -euo pipefail

THREAD_ID="${1:?Usage: resolve-thread.sh <thread_id>}"

MUTATION='mutation($tid:ID!){
  resolveReviewThread(input:{threadId:$tid}){
    thread{ id isResolved }
  }
}'

response=$(gh api graphql -f query="$MUTATION" -F tid="$THREAD_ID" 2>&1) || {
  echo "Error: resolve thread $THREAD_ID failed: $response" >&2
  exit 1
}

if echo "$response" | jq -e '.errors // empty' >/dev/null 2>&1; then
  echo "Error: GraphQL error: $(echo "$response" | jq -r '.errors[0].message')" >&2
  exit 1
fi

echo "-#-#- RESULT -#-#-"
echo "- thread_id: $THREAD_ID"
echo "- isResolved: $(echo "$response" | jq -r '.data.resolveReviewThread.thread.isResolved')"
