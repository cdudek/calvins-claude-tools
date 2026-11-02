#!/usr/bin/env bash
# Usage: pr-checks.sh <pr_number>
# Detailed CI check list — name, state, bucket, link, description, workflow.
# Use this when you need per-check details (e.g., to find failed run IDs);
# use pr-readiness.sh when you only need the pass/fail/pending summary.
# Output: opaque JSONL content delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- BEGIN CI_CHECKS -#-#- ... -#-#- END CI_CHECKS -#-#-
# Content: one JSON object per line, fields: name, state, bucket, link, description, workflow.
# Prints `NO_CHECKS` inside the section if no checks are configured.
set -euo pipefail

PR="${1:?Usage: pr-checks.sh <pr_number>}"

echo "-#-#- BEGIN CI_CHECKS -#-#-"
if ! gh pr checks "$PR" --json name,state,bucket,link,description,workflow \
  --jq '.[] | {name, state, bucket, link, description, workflow}' 2>/dev/null; then
  echo "NO_CHECKS"
fi
echo "-#-#- END CI_CHECKS -#-#-"
