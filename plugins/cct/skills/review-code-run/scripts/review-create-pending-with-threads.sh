#!/usr/bin/env bash
# Usage: cat findings.json | review-create-pending-with-threads.sh <pr_node_id>
# One-shot variant: creates a pending review with all `new`-action threads inline.
# Used in Scenario A when there are `new`-action findings to post.
#
# Input (stdin): JSON array of findings:
#   [{"path": str, "line": int, "side": "LEFT"|"RIGHT", "body": str,
#     "start_line"?: int, "start_side"?: "LEFT"|"RIGHT"}, ...]
#
# Reliability advantage: GitHub either anchors all threads or fails the whole mutation —
# no silent-null per-thread risk (community discussion #182548).
#
# Output: {"review_node_id": "PRR_..."}
#
# Note: thread node_ids of the new threads are NOT returned. The downstream flow
# (replies/reopens, submit, unresolves) operates on EXISTING thread IDs from
# thread reconciliation, never on the just-created new threads.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <pr_node_id>" >&2
  echo "  Reads JSON array of findings from stdin." >&2
  exit 2
fi

PR_NODE_ID="$1"
FINDINGS=$(cat)

if [[ -z "$FINDINGS" ]] || ! echo "$FINDINGS" | jq -e 'type == "array" and length > 0' >/dev/null; then
  echo "Error: stdin must be a non-empty JSON array of findings" >&2
  exit 2
fi

THREADS=$(echo "$FINDINGS" | jq -c '
  map({
    path: .path,
    line: .line,
    side: .side,
    body: .body
  } + (
    if (has("start_line") and .start_line != null)
    then {startLine: .start_line, startSide: (.start_side // .side)}
    else {}
    end
  ))
')

QUERY='mutation($pr: ID!, $threads: [DraftPullRequestReviewThread!]) {
  addPullRequestReview(input: {pullRequestId: $pr, threads: $threads}) {
    pullRequestReview { id }
  }
}'

REQUEST=$(jq -nc \
  --arg query "$QUERY" \
  --arg pr "$PR_NODE_ID" \
  --argjson threads "$THREADS" \
  '{query: $query, variables: {pr: $pr, threads: $threads}}')

RESPONSE=$(echo "$REQUEST" | gh api graphql --input -)

REVIEW_ID=$(echo "$RESPONSE" | jq -r '.data.addPullRequestReview.pullRequestReview.id // empty')

if [[ -z "$REVIEW_ID" ]]; then
  echo "Error: addPullRequestReview returned null pullRequestReview" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

jq -nc --arg id "$REVIEW_ID" '{review_node_id: $id}'
