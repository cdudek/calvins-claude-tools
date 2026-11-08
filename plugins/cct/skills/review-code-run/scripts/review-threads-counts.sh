#!/usr/bin/env bash
# Usage: review-threads-counts.sh <threads_file> [pending_review_json]
# Extracts action-plan header counts from a threads JSON file written by review-threads.sh.
#
# Output (stdout): shell-eval-able assignments, one per line. Run via:
#   eval "$(bash review-threads-counts.sh <file> "$PENDING_REVIEW")"
# This sets four shell variables:
#   THREADS_TOTAL          — total thread count
#   THREADS_RESOLVED       — count of resolved threads
#   THREADS_OWN_ACTIVE     — count of unresolved threads whose first comment's author
#                            matches current_user (extracted from pending_review_json)
#   THREADS_OTHERS_ACTIVE  — TOTAL − RESOLVED − OWN_ACTIVE
#
# If pending_review_json is empty or missing, current_user defaults to empty —
# OWN_ACTIVE will be 0 and OTHERS_ACTIVE will be (TOTAL − RESOLVED).
#
# Safety: threads_file must be under ${TMPDIR:-/tmp} or /tmp/.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but not installed." >&2
  exit 2
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <threads_file> [pending_review_json]" >&2
  exit 2
fi

THREADS_FILE="$1"
PENDING_REVIEW_JSON="${2:-}"

case "$THREADS_FILE" in
  "${TMPDIR:-/tmp}"/*|/tmp/*) ;;
  *)
    echo "Error: threads_file must be under \${TMPDIR:-/tmp} or /tmp/ (got: $THREADS_FILE)" >&2
    exit 2
    ;;
esac

if [[ ! -f "$THREADS_FILE" ]]; then
  echo "Error: threads_file not found: $THREADS_FILE" >&2
  exit 2
fi

CURRENT_USER=""
if [[ -n "$PENDING_REVIEW_JSON" ]]; then
  CURRENT_USER=$(echo "$PENDING_REVIEW_JSON" | jq -r '.current_user // ""')
fi

jq -r --arg u "$CURRENT_USER" '
  (.threads // []) as $t
  | ($t | length) as $total
  | ([$t[] | select(.isResolved)] | length) as $resolved
  | ([$t[] | select(.isResolved | not) | select(($u != "") and (.comments.nodes[0].author.login == $u))] | length) as $own
  | "THREADS_TOTAL=\($total)\nTHREADS_RESOLVED=\($resolved)\nTHREADS_OWN_ACTIVE=\($own)\nTHREADS_OTHERS_ACTIVE=\($total - $resolved - $own)"
' "$THREADS_FILE"
