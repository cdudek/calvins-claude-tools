#!/usr/bin/env bash
# Usage: review-threads.sh <owner> <repo> <pr_number> <output_path>
# Fetches all review threads via GraphQL, writes JSON to <output_path>, echoes the path.
# Called from the main thread, not the thread-reconciliation subagent.
#
# Output:
# - stdout: the output_path (single line)
# - file at output_path: {"pr_node_id": "PR_...", "threads": [...]}
#
# Safety: output_path must be under ${TMPDIR:-/tmp} or /tmp/.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> <output_path>" >&2
  exit 2
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
OUTPUT_PATH="$4"

if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
  echo "Error: pr_number must be a positive integer (got: $PR_NUMBER)" >&2
  exit 2
fi

case "$OUTPUT_PATH" in
  "${TMPDIR:-/tmp}"/*|/tmp/*) ;;
  *)
    echo "Error: output_path must be under \${TMPDIR:-/tmp} or /tmp/ (got: $OUTPUT_PATH)" >&2
    exit 2
    ;;
esac

# reviewThreads/comments use first: 100 — GraphQL's max page size; the post-query
# guards below warn when either connection hits the cap (these are not paginated).
if ! gh api graphql -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      id
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          line
          startLine
          path
          diffSide
          comments(first: 100) {
            nodes {
              id
              databaseId
              body
              author { login }
              pullRequestReview { id state }
            }
          }
        }
      }
    }
  }
}' -f owner="$OWNER" -f repo="$REPO" -F number="$PR_NUMBER" --jq '{pr_node_id: .data.repository.pullRequest.id, threads: .data.repository.pullRequest.reviewThreads.nodes}' > "$OUTPUT_PATH"; then
  echo "Error: GraphQL query failed (network/auth?). args: owner=${OWNER} repo=${REPO} pr_number=${PR_NUMBER}" >&2
  rm -f "$OUTPUT_PATH"
  exit 1
fi

# Guard against null-propagation: gh exits 0 and --jq writes
# {"pr_node_id": null, "threads": null} when owner/repo/pr_number don't resolve
# to a real PR. Network/auth failures are caught above — the `> "$OUTPUT_PATH"`
# redirection creates an empty file before gh runs, so the failure path removes it.
if ! jq -e '.pr_node_id != null and .threads != null' "$OUTPUT_PATH" >/dev/null 2>&1; then
  echo "Error: GraphQL query returned null (PR not found?). args: owner=${OWNER} repo=${REPO} pr_number=${PR_NUMBER}" >&2
  rm -f "$OUTPUT_PATH"
  exit 1
fi

# Warn when a connection hit the 100-record page cap: these connections are not
# paginated, so anything beyond 100 is silently dropped and downstream
# thread reconciliation may miss the overflow.
if [[ "$(jq '.threads | length' "$OUTPUT_PATH")" -eq 100 ]]; then
  echo "Warning: reviewThreads returned the maximum 100 records; additional threads were not fetched (no pagination)." >&2
fi
truncated_comments="$(jq -r '.threads[] | select((.comments.nodes | length) == 100) | .id' "$OUTPUT_PATH" | tr '\n' ' ')"
if [[ -n "$truncated_comments" ]]; then
  echo "Warning: these threads returned the maximum 100 comments and may be truncated: ${truncated_comments% }" >&2
fi

echo "$OUTPUT_PATH"
