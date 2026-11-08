#!/usr/bin/env bash
# Usage: cat body.md | review-reply.sh <thread_node_id> <review_node_id>
# Replies to an existing thread, attached to the given pending review.
# The reply stays pending until the review is submitted (pullRequestReviewId is what keeps it pending).
#
# Body: read from stdin.
#
# Output: {"comment_id": "PRRC_..."}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <thread_node_id> <review_node_id>" >&2
  echo "  Body read from stdin." >&2
  exit 2
fi

THREAD_NODE_ID="$1"
REVIEW_NODE_ID="$2"
BODY=$(cat)

if [[ -z "$BODY" ]]; then
  echo "Error: body must not be empty (read from stdin)" >&2
  exit 2
fi

QUERY='mutation($thread: ID!, $review: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: $thread,
    pullRequestReviewId: $review,
    body: $body
  }) { comment { id } }
}'

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --arg thread "$THREAD_NODE_ID" \
  --arg review "$REVIEW_NODE_ID" \
  --arg body "$BODY" \
  '{query: $query, variables: {thread: $thread, review: $review, body: $body}}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

COMMENT_ID=$(echo "$RESPONSE" | jq -r '.data.addPullRequestReviewThreadReply.comment.id // empty')

if [[ -z "$COMMENT_ID" ]]; then
  echo "Error: addPullRequestReviewThreadReply returned null comment" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc --arg id "$COMMENT_ID" '{comment_id: $id}'
