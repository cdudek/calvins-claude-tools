#!/usr/bin/env bash
# Usage: cat body.md | review-add-thread.sh <review_node_id> <path> <line> <side> [<start_line> <start_side>]
# Adds a new comment thread to an existing pending review.
# Used in Scenario B (pending review already exists).
#
# Body: read from stdin.
# side: LEFT | RIGHT (GraphQL DiffSide enum).
#
# Reliability: GitHub validates the diff anchor (commit OID + hunk). On failure it can
# return {"thread": null} without a GraphQL error — set -euo pipefail will NOT catch this.
# The script jq-checks .thread.id and exits non-zero (with the raw response on stderr)
# when the thread is null. See community discussion #182548.
#
# Output: {"thread_id": "PRRT_..."}
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -lt 4 || $# -gt 6 ]]; then
  echo "Usage: $0 <review_node_id> <path> <line> <side> [<start_line> <start_side>]" >&2
  echo "  Body read from stdin." >&2
  exit 2
fi

REVIEW_NODE_ID="$1"
FILE_PATH="$2"
LINE="$3"
SIDE="$4"
START_LINE="${5:-}"
START_SIDE="${6:-}"

BODY=$(cat)

if [[ -z "$BODY" ]]; then
  echo "Error: body must not be empty (read from stdin)" >&2
  exit 2
fi

VARIABLES=$(jq -nc \
  --arg review "$REVIEW_NODE_ID" \
  --arg body "$BODY" \
  --arg path "$FILE_PATH" \
  --argjson line "$LINE" \
  --arg side "$SIDE" \
  '{review: $review, body: $body, path: $path, line: $line, side: $side}')

if [[ -n "$START_LINE" ]]; then
  VARIABLES=$(echo "$VARIABLES" | jq -c \
    --argjson sl "$START_LINE" \
    --arg ss "${START_SIDE:-$SIDE}" \
    '. + {startLine: $sl, startSide: $ss}')
  QUERY='mutation($review: ID!, $body: String!, $path: String!, $line: Int!, $side: DiffSide!, $startLine: Int!, $startSide: DiffSide!) {
    addPullRequestReviewThread(input: {
      pullRequestReviewId: $review,
      body: $body,
      path: $path,
      line: $line,
      side: $side,
      startLine: $startLine,
      startSide: $startSide
    }) { thread { id } }
  }'
else
  QUERY='mutation($review: ID!, $body: String!, $path: String!, $line: Int!, $side: DiffSide!) {
    addPullRequestReviewThread(input: {
      pullRequestReviewId: $review,
      body: $body,
      path: $path,
      line: $line,
      side: $side
    }) { thread { id } }
  }'
fi

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --argjson variables "$VARIABLES" \
  '{query: $query, variables: $variables}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

THREAD_ID=$(echo "$RESPONSE" | jq -r '.data.addPullRequestReviewThread.thread.id // empty')

if [[ -z "$THREAD_ID" ]]; then
  echo "Error: addPullRequestReviewThread returned null thread (silent-null failure)." >&2
  echo "Likely cause: GitHub could not resolve the diff anchor (commit OID + hunk)." >&2
  echo "See community discussion #182548. Raw response:" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc --arg id "$THREAD_ID" '{thread_id: $id}'
