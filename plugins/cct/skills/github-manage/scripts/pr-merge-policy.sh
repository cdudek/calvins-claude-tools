#!/usr/bin/env bash
# Usage: pr-merge-policy.sh
# Dumps the current repo's merge policy.
# Uses the REST API because `gh repo view --json` does not expose
# squashMergeCommitTitle / squashMergeCommitMessage.
# Output: section delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- REPO_MERGE_POLICY -#-#-   (key-value)
set -euo pipefail

OWNER_REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
DATA=$(gh api "repos/$OWNER_REPO")

echo "-#-#- REPO_MERGE_POLICY -#-#-"
echo "- merge_allowed: $(echo "$DATA" | jq -r '.allow_merge_commit')"
echo "- squash_allowed: $(echo "$DATA" | jq -r '.allow_squash_merge')"
echo "- rebase_allowed: $(echo "$DATA" | jq -r '.allow_rebase_merge')"
echo "- default_squash_title: $(echo "$DATA" | jq -r '.squash_merge_commit_title // "PR_TITLE"')"
echo "- default_squash_body: $(echo "$DATA" | jq -r '.squash_merge_commit_message // "COMMIT_MESSAGES"')"
