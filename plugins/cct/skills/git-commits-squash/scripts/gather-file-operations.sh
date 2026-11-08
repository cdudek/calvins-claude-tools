#!/usr/bin/env bash
# Usage: gather-file-operations.sh <base-branch>
# Gathers file-level operations: renames, adds, deletes, per-commit operations.
# Used for inconsistency detection (contradictory changes, incomplete operations).
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- BEGIN DIFF_STATS -#-#- ... -#-#- END DIFF_STATS -#-#-                     (git --stat output)
#   -#-#- BEGIN DIFF_NUMSTAT -#-#- ... -#-#- END DIFF_NUMSTAT -#-#-                 (git --numstat output)
#   -#-#- BEGIN FILE_OPERATIONS -#-#- ... -#-#- END FILE_OPERATIONS -#-#-           (git --name-status --find-renames)
#   -#-#- BEGIN PER_COMMIT_OPERATIONS -#-#- ... -#-#- END PER_COMMIT_OPERATIONS -#-#- (per-commit --name-status; opaque)
#   -#-#- CONTRADICTIONS -#-#-      (list, one path per line, or `- none`)
#   -#-#- NET_ZERO_FILES -#-#-      (list, one path per line, or `- none`)
set -euo pipefail

BASE="${1:?Usage: gather-file-operations.sh <base-branch>}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)

echo "-#-#- BEGIN DIFF_STATS -#-#-"
git diff "$MERGE_BASE"...HEAD --stat
echo "-#-#- END DIFF_STATS -#-#-"

echo ""
echo "-#-#- BEGIN DIFF_NUMSTAT -#-#-"
git diff "$MERGE_BASE"...HEAD --numstat
echo "-#-#- END DIFF_NUMSTAT -#-#-"

echo ""
echo "-#-#- BEGIN FILE_OPERATIONS -#-#-"
git diff "$MERGE_BASE"...HEAD --name-status --find-renames
echo "-#-#- END FILE_OPERATIONS -#-#-"

echo ""
echo "-#-#- BEGIN PER_COMMIT_OPERATIONS -#-#-"
git log "$MERGE_BASE"..HEAD --format="### %H %s" --name-status
echo "-#-#- END PER_COMMIT_OPERATIONS -#-#-"

echo ""
echo "-#-#- CONTRADICTIONS -#-#-"
ADDED=$(git log "$MERGE_BASE"..HEAD --diff-filter=A --name-only --format="" | awk 'NF' | sort -u)
DELETED=$(git log "$MERGE_BASE"..HEAD --diff-filter=D --name-only --format="" | awk 'NF' | sort -u)
if [ -n "$ADDED" ] && [ -n "$DELETED" ]; then
  CONTRADICTIONS=$(comm -12 <(echo "$ADDED") <(echo "$DELETED"))
  if [ -n "$CONTRADICTIONS" ]; then
    echo "$CONTRADICTIONS"
  else
    echo "- none"
  fi
else
  echo "- none"
fi

echo ""
echo "-#-#- NET_ZERO_FILES -#-#-"
NET_ZERO=$(git diff "$MERGE_BASE"...HEAD --numstat | awk '$1 == "0" && $2 == "0" { print $3 }')
if [ -n "$NET_ZERO" ]; then
  echo "$NET_ZERO"
else
  echo "- none"
fi
