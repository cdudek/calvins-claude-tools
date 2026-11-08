#!/usr/bin/env bash
# Usage: save-pr-diff.sh <base_branch> <output_path>
# Generates the PR diff locally from the checked-out worktree and writes it to
# <output_path>. Uses git three-dot diff (merge-base semantics — matches
# GitHub's "Files changed" view), so it works on arbitrarily large PRs without
# the API size ceiling / truncation of `gh pr diff`.
#
# Precondition: CWD is the review worktree checked out on the PR head branch
# (HEAD == PR head). Both PR modes (pr-deep, pr-max) enter such a worktree.
#
# Output sections:
#   -#-#- DIFF -#-#-
#   - path: <output_path>
#   - base: origin/<base_branch>
#   - lines: <N>

set -euo pipefail

BASE="${1:?usage: save-pr-diff.sh <base_branch> <output_path>}"
OUT="${2:?usage: save-pr-diff.sh <base_branch> <output_path>}"

# Ensure the base ref is present locally; updates refs/remotes/origin/<base>.
# `--` guards against a base branch name that begins with `-` being read as a flag.
git fetch --quiet origin -- "$BASE"

git diff "origin/${BASE}...HEAD" > "$OUT"

lines=$(wc -l < "$OUT")
printf -- '-#-#- DIFF -#-#-\n'
printf -- '- path: %s\n' "$OUT"
printf -- '- base: origin/%s\n' "$BASE"
printf -- '- lines: %s\n' "$lines"
