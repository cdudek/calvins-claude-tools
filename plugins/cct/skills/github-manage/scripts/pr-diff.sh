#!/usr/bin/env bash
# Usage: pr-diff.sh <pr_number>
# Dumps the full PR diff. Kept separate from pr-context.sh because diffs can be
# very large; callers that don't need the diff should not pay the context cost.
# Output: opaque content delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- BEGIN PR_DIFF -#-#- ... -#-#- END PR_DIFF -#-#-
set -euo pipefail

PR="${1:?Usage: pr-diff.sh <pr_number>}"

echo "-#-#- BEGIN PR_DIFF -#-#-"
gh pr diff "$PR"
echo "-#-#- END PR_DIFF -#-#-"
