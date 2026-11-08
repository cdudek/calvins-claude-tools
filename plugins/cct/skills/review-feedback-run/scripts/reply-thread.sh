#!/usr/bin/env bash
# Post a reply to a PR review thread (in-reply-to its first comment).
# Usage: reply-thread.sh <pr_number> <comment_id> <body_or_- (read stdin)>
#   pr_number:  numeric PR
#   comment_id: REST databaseId of the thread's first comment (from gather REVIEW_THREADS.comments[0].comment_id)
#   body:       reply text, or `-` to read body from stdin (useful for multiline)
# Output: -#-#- RESULT -#-#- with reply_id and url
set -euo pipefail

PR_NUMBER="${1:?Usage: reply-thread.sh <pr_number> <comment_id> <body|->}"
COMMENT_ID="${2:?Usage: reply-thread.sh <pr_number> <comment_id> <body|->}"
BODY_ARG="${3:?Usage: reply-thread.sh <pr_number> <comment_id> <body|->}"

[[ "$PR_NUMBER" =~ ^[0-9]+$ ]] || { echo "Error: PR number must be numeric"; exit 1; }
[[ "$COMMENT_ID" =~ ^[0-9]+$ ]] || { echo "Error: comment_id must be numeric (REST databaseId)"; exit 1; }

if [ "$BODY_ARG" = "-" ]; then
  BODY=$(cat)
else
  BODY="$BODY_ARG"
fi

OWNER=$(gh repo view --json owner -q '.owner.login')
REPO=$(gh repo view --json name -q '.name')

response=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments/$COMMENT_ID/replies" -f body="$BODY" 2>&1) || {
  echo "Error: reply to PR #$PR_NUMBER comment $COMMENT_ID failed: $response" >&2
  exit 1
}

echo "-#-#- RESULT -#-#-"
echo "- reply_id: $(echo "$response" | jq -r '.id')"
echo "- url: $(echo "$response" | jq -r '.html_url')"
