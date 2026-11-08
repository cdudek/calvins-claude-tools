#!/usr/bin/env bash
# Usage: pr-squash-merge.sh <pr_number> <subject> [--auto]
# Squash-merges a GitHub PR with the given subject. Body is read from stdin.
# Pass --auto to queue with `gh pr merge --auto` so GitHub merges when all
# branch-protection requirements are met.
# Output: gh pr merge output (URL / status).
#
# DESTRUCTIVE: this mutates a shared remote (squash-merges the PR). Only call
# from `/squash pr`, which gates on the user's y/auto/n confirmation. Direct
# invocation skips that gate.
set -euo pipefail

PR="${1:?Usage: pr-squash-merge.sh <pr_number> <subject> [--auto]}"
SUBJECT="${2:?Usage: pr-squash-merge.sh <pr_number> <subject> [--auto]}"
if [ -z "$SUBJECT" ] || [[ "$SUBJECT" == --* ]]; then
  echo "pr-squash-merge.sh: invalid subject '$SUBJECT' (empty or flag-shaped)" >&2
  exit 1
fi
AUTO=()
[ "${3:-}" = "--auto" ] && AUTO=(--auto)

gh pr merge "$PR" --squash "${AUTO[@]}" -t "$SUBJECT" -F -
