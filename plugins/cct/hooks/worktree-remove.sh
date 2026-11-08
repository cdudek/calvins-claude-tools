#!/usr/bin/env bash
# hook-event: WorktreeRemove
# hook-timeout: 120
# hook-status: Removing worktree...
#
# Pairs with worktree-create.sh. Removes the worktree and its local branch (the
# branch is already pushed by the time a worktree is finished with; if it is not,
# ExitWorktree refuses before this hook runs).

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.worktree_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

[ -n "$WORKTREE_PATH" ] || exit 0
[[ "$WORKTREE_PATH" == /* ]] || exit 0

GIT_ROOT=$(cd "$CWD" && git rev-parse --git-common-dir 2>/dev/null | xargs -I{} sh -c 'cd "{}" && cd .. && pwd')
[ -n "$GIT_ROOT" ] || exit 0

BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null)

if git -C "$GIT_ROOT" worktree remove "$WORKTREE_PATH" --force > /dev/null 2>&1; then
    [ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] && git -C "$GIT_ROOT" branch -D "$BRANCH" > /dev/null 2>&1
else
    rm -rf "$WORKTREE_PATH" 2>/dev/null
    git -C "$GIT_ROOT" worktree prune > /dev/null 2>&1
fi

exit 0
