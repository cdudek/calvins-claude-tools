#!/usr/bin/env bash
# Usage: cat new_body.md | review-update-comment.sh <owner> <repo> <comment_database_id>
# Updates an existing PR review comment's body via REST PATCH.
# Used for the `append` action — caller composes original body + delimiter + new context before piping.
#
# comment_database_id is the numeric databaseId, NOT the GraphQL node_id.
#
# Output: the updated comment JSON from GitHub.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <owner> <repo> <comment_database_id>" >&2
  echo "  Body read from stdin." >&2
  exit 2
fi

OWNER="$1"
REPO="$2"
COMMENT_ID="$3"
BODY=$(cat)

if [[ -z "$BODY" ]]; then
  echo "Error: body must not be empty (read from stdin)" >&2
  exit 2
fi

gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}" \
  -X PATCH \
  -f body="$BODY"
