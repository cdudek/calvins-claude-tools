#!/usr/bin/env bash
# hook-event: WorktreeRemove
# hook-timeout: 120
# hook-status: Removing clean worktree...
# Refuse dirty worktrees even when other WorktreeRemove hooks run concurrently.
# No force, filesystem deletion or repository-wide prune; keep unmerged branches.

set -uo pipefail
INPUT=$(cat)
WORKTREE_PATH=$(printf '%s' "$INPUT" | jq -r '.worktree_path // empty')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // "."')
[ -n "$WORKTREE_PATH" ] || exit 0
[[ "$WORKTREE_PATH" == /* ]] || { echo "Refusing non-absolute worktree path" >&2; exit 1; }
GIT_COMMON=$(git -C "$CWD" rev-parse --path-format=absolute --git-common-dir) || exit 1
GIT_ROOT=$(cd "$GIT_COMMON/.." && pwd -P) || exit 1
WORKTREE_PATH=$(cd "$WORKTREE_PATH" && pwd -P) || exit 1
case "$WORKTREE_PATH" in "$GIT_ROOT"/.worktrees/*) ;; *) echo "Refusing worktree outside this repo's .worktrees" >&2; exit 1 ;; esac
# See ../references/worktree-usage.md for the Worktrunk-first policy.
if command -v wt >/dev/null 2>&1; then
    LIST=$(command wt -C "$GIT_ROOT" list --format json) || exit 1
    printf '%s' "$LIST" | jq -e --arg path "$WORKTREE_PATH" \
        'if type == "array" then . else .items end | any(.[]; (.worktree.path // .path) == $path)' >/dev/null || { echo "Refusing unregistered worktree: $WORKTREE_PATH" >&2; exit 1; }
else
    git -C "$GIT_ROOT" worktree list --porcelain | grep -qxF "worktree $WORKTREE_PATH" || { echo "Refusing unregistered worktree: $WORKTREE_PATH" >&2; exit 1; }
fi
DIRTY=$(git -C "$WORKTREE_PATH" status --porcelain --untracked-files=all --ignored=matching) || exit 1
if [ -n "$DIRTY" ]; then
    echo "Refusing to remove dirty worktree: $WORKTREE_PATH; commit or move all changes and untracked files first. Everything was kept." >&2
    exit 1
fi
BRANCH=$(git -C "$WORKTREE_PATH" symbolic-ref -q --short HEAD) || BRANCH=""
# No force: Git also checks again if files change after our preflight.
if command -v wt >/dev/null 2>&1; then
    command wt -C "$GIT_ROOT" remove "$WORKTREE_PATH" --no-delete-branch --foreground --format json --no-hooks >&2 || exit 1
else
    git -C "$GIT_ROOT" worktree remove "$WORKTREE_PATH" || exit 1
fi
if [ -n "$BRANCH" ]; then
    if ! git -C "$GIT_ROOT" branch -d "$BRANCH" >&2; then
        echo "Worktree removed; branch $BRANCH kept because Git did not confirm it merged. Review its commits before deleting it." >&2
    fi
fi
