#!/usr/bin/env bash
# Usage: gather-full-diff.sh <base-branch>
# Outputs the full diff between merge-base and HEAD.
# Separated from other scripts to keep context manageable —
# only loaded when the analysis agent needs the actual code changes.
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- BEGIN FULL_DIFF -#-#- ... -#-#- END FULL_DIFF -#-#- (opaque diff)
set -euo pipefail

BASE="${1:?Usage: gather-full-diff.sh <base-branch>}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)

echo "-#-#- BEGIN FULL_DIFF -#-#-"
git diff "$MERGE_BASE"...HEAD
echo "-#-#- END FULL_DIFF -#-#-"
