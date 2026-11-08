#!/usr/bin/env bash
# Usage: gather-branch-info.sh <base-branch>
# Gathers branch metadata, commit list, and ticket references.
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- BRANCH_INFO -#-#-       (key-value)
#   -#-#- SAFETY -#-#-            (key-value)
#   -#-#- REMOTE -#-#-            (key-value)
#   -#-#- SCALE -#-#-             (key-value)
#   -#-#- COMMITS -#-#-           (repeating commits, each ended by -#-#- END COMMIT -#-#-)
#   -#-#- TICKET_REFERENCES -#-#- (key-value: branch_linear, commits_linear, github)
#   -#-#- CO_AUTHORS -#-#-        (list, one per line, or single `- none`)
set -euo pipefail

BASE="${1:?Usage: gather-branch-info.sh <base-branch>}"
HEAD_SHA=$(git rev-parse HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "HEAD" ]; then
  echo "ERROR: Detached HEAD state. Check out a branch first." >&2
  exit 1
fi
MERGE_BASE=$(git merge-base "$BASE" HEAD)
COMMIT_COUNT=$(git rev-list "$MERGE_BASE"..HEAD --count)

echo "-#-#- BRANCH_INFO -#-#-"
echo "- branch: $BRANCH"
echo "- base: $BASE"
echo "- head: $HEAD_SHA"
echo "- merge_base: $MERGE_BASE"
echo "- commit_count: $COMMIT_COUNT"

echo ""
echo "-#-#- SAFETY -#-#-"
PROTECTED="false"
for p in main master develop production staging; do
  [ "$BRANCH" = "$p" ] && PROTECTED="true" && break
done
echo "- on_protected_branch: $PROTECTED"

echo ""
echo "-#-#- REMOTE -#-#-"
if UPSTREAM=$(git rev-parse --abbrev-ref "@{upstream}" 2>/dev/null); then
  echo "- upstream: $UPSTREAM"
  echo "- push_required: true"
else
  echo "- upstream: none"
  echo "- push_required: false"
fi

echo ""
echo "-#-#- SCALE -#-#-"
FILES_CHANGED=$(git diff "$MERGE_BASE"...HEAD --name-only | wc -l | tr -d ' ')
INSERTIONS=$(git diff "$MERGE_BASE"...HEAD --shortstat | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
DELETIONS=$(git diff "$MERGE_BASE"...HEAD --shortstat | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")
echo "- files_changed: $FILES_CHANGED"
echo "- insertions: $INSERTIONS"
echo "- deletions: $DELETIONS"

echo ""
echo "-#-#- COMMITS -#-#-"
# Bodies may contain arbitrary markdown including ## headers and code fences,
# so each commit is terminated by an explicit END COMMIT marker.
git log "$MERGE_BASE"..HEAD --format="### %H%nsubject: %s%nauthor: %an <%ae>%ndate: %ai%nbody:%n%b-#-#- END COMMIT -#-#-"

echo ""
echo "-#-#- TICKET_REFERENCES -#-#-"
BRANCH_LINEAR=$(echo "$BRANCH" | grep -oE '[A-Z]+-[0-9]+' | paste -sd, - || true)
COMMITS_LINEAR=$(git log "$MERGE_BASE"..HEAD --format="%s %b" | grep -oE '[A-Z]+-[0-9]+' | sort -u | paste -sd, - || true)
GITHUB_REFS=$(git log "$MERGE_BASE"..HEAD --format="%s %b" | grep -oE '#[0-9]+' | sort -u | paste -sd, - || true)
echo "- branch_linear: ${BRANCH_LINEAR:-none}"
echo "- commits_linear: ${COMMITS_LINEAR:-none}"
echo "- github: ${GITHUB_REFS:-none}"

echo ""
echo "-#-#- CO_AUTHORS -#-#-"
CO_AUTHORS=$(git log "$MERGE_BASE"..HEAD --format="%b" | grep -i "co-authored-by" | sort -u || true)
echo "${CO_AUTHORS:-- none}"
