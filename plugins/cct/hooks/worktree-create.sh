#!/usr/bin/env bash
# hook-event: WorktreeCreate
# hook-timeout: 120
# hook-status: Creating worktree...
#
# Every worktree lands at <repo>/.worktrees/<name>. No exceptions, no siblings.
#
# Once, three worktrees were created as siblings of the repo, in the projects dir. The
# equivalent plugin hook was not active (the plugin was not enabled), so Claude Code's
# built-in placement ran instead.
# This copy lives in ~/.claude/hooks and is registered directly in settings.json, so
# it cannot be switched off by a plugin being disabled.
#
# Unlike the plugin version, an absolute or ./relative path does NOT escape: it is
# reduced to its basename under .worktrees/. "Never ever anywhere else" is the rule.
#
# Format: name[@target-branch[@base-branch]] or @target-branch[@base-branch]
#   my-feature                     -> .worktrees/my-feature, branch my-feature from origin/master
#   my-feature@feat/login          -> .worktrees/my-feature, branch feat/login from origin/master
#   my-feature@feat/login@develop  -> .worktrees/my-feature, branch feat/login from develop
#   @feat/login                    -> .worktrees/login, branch feat/login from origin/master

INPUT=$(cat)
RAW_NAME=$(echo "$INPUT" | jq -r '.name // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

GIT_ROOT=$(cd "$CWD" && git rev-parse --git-common-dir 2>/dev/null | xargs -I{} sh -c 'cd "{}" && cd .. && pwd -P')
[ -n "$GIT_ROOT" ] || { echo "Not a git repository: $CWD" >&2; exit 1; }

# NEVER NEST. A second clone of the repo was sitting at
# <workspace>/.worktrees/data-model-repository, so --git-common-dir resolved GIT_ROOT to
# THAT clone and the new worktree landed at .worktrees/data-model-repository/.worktrees/<name>
# — two levels deep, which CLAUDE.md forbids outright. A worktree inside a worktree also
# hides from `ls .worktrees/` at the level anyone actually looks.
#
# If GIT_ROOT sits under a .worktrees/ directory, climb to the parent of the OUTERMOST one.
# That is the workspace root whatever the checkout layout underneath happens to be.
case "$GIT_ROOT" in
  */.worktrees/*)
    GIT_ROOT="${GIT_ROOT%%/.worktrees/*}"
    ;;
esac

IFS='@' read -r RAW_PATH TARGET_BRANCH BASE_BRANCH <<< "$RAW_NAME"

# Basename only — an absolute or relative path is stripped, never honoured.
NAME="${RAW_PATH##*/}"
[ -z "$NAME" ] && NAME="${TARGET_BRANCH##*/}"
[ -z "$NAME" ] && NAME="wt-$(date +%s)"
case "$NAME" in .|..) echo "Invalid worktree name: $NAME" >&2; exit 1 ;; esac
WORKTREE_PATH="$GIT_ROOT/.worktrees/$NAME"

[ -z "$TARGET_BRANCH" ] && TARGET_BRANCH="$NAME"

# Belt to the global gitignore's `.worktrees/`: repos that override core.excludesfile
# still never see the directory as untracked.
# Absolute: a relative ".git" resolves against the hook's cwd, which is a worktree
# (where .git is a file) when the session runs inside one.
EXCLUDE="$(git -C "$GIT_ROOT" rev-parse --path-format=absolute --git-common-dir)/info/exclude"
mkdir -p "$(dirname "$EXCLUDE")" 2>/dev/null
grep -qxF '.worktrees/' "$EXCLUDE" 2>/dev/null || echo '.worktrees/' >> "$EXCLUDE"

# Default base: the remote default branch, fetched now — an isolated session cannot
# see or update the main checkout, so "whatever is checked out there" starts stale.
if [ -z "$BASE_BRANCH" ]; then
    if git -C "$GIT_ROOT" remote get-url origin > /dev/null 2>&1; then
        git -C "$GIT_ROOT" fetch -q origin || { echo "Failed to fetch origin; refusing a stale base" >&2; exit 1; }
        DEFAULT=$(git -C "$GIT_ROOT" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
        if [ -z "$DEFAULT" ]; then
            for cand in master main; do
                git -C "$GIT_ROOT" rev-parse -q --verify "refs/remotes/origin/$cand" > /dev/null 2>&1 && DEFAULT="$cand" && break
            done
        fi
        [ -n "$DEFAULT" ] && BASE_BRANCH="origin/$DEFAULT"
    fi
    if [ -z "$BASE_BRANCH" ]; then
        for cand in master main; do
            git -C "$GIT_ROOT" rev-parse -q --verify "refs/heads/$cand" > /dev/null 2>&1 && BASE_BRANCH="$cand" && break
        done
    fi
    [ -n "$BASE_BRANCH" ] || BASE_BRANCH=HEAD
fi

# See ../references/worktree-usage.md. Never invoke the shell integration or prompt.
if command -v wt >/dev/null 2>&1; then
    PATH_CONFIG="worktree-path = $(printf '%s' "$WORKTREE_PATH" | jq -Rs .)"
    if git -C "$GIT_ROOT" show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
        RESULT=$(command wt -C "$GIT_ROOT" switch "$TARGET_BRANCH" --no-cd --format json --no-hooks --config-set "$PATH_CONFIG")
    else
        RESULT=$(command wt -C "$GIT_ROOT" switch -c "$TARGET_BRANCH" -b "$BASE_BRANCH" --no-cd --format json --no-hooks --config-set "$PATH_CONFIG")
    fi
    STATUS=$?
    # Creation can succeed before a later error: never fall back and create twice.
    [ "$STATUS" -eq 0 ] || { echo "Worktrunk failed: $RESULT" >&2; exit "$STATUS"; }
    CREATED_PATH=$(printf '%s' "$RESULT" | jq -er '.path') || exit 1
    [ "$CREATED_PATH" = "$WORKTREE_PATH" ] || { echo "Branch is checked out elsewhere: $CREATED_PATH" >&2; exit 1; }
    if [ "$(printf '%s' "$RESULT" | jq -r '.created_branch')" = true ]; then
        git -C "$GIT_ROOT" branch --unset-upstream "$TARGET_BRANCH" >/dev/null 2>&1 || true
    fi
    cd "$CREATED_PATH" && pwd
    exit $?
fi

RESOLVED_PATH=$(cd "$WORKTREE_PATH" 2>/dev/null && pwd)
if [ -n "$RESOLVED_PATH" ] && git -C "$GIT_ROOT" worktree list --porcelain | grep -qxF "worktree $RESOLVED_PATH"; then
    echo "$RESOLVED_PATH"
    exit 0
fi

mkdir -p "$(dirname "$WORKTREE_PATH")" > /dev/null 2>&1
if git -C "$GIT_ROOT" show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
    git -C "$GIT_ROOT" worktree add "$WORKTREE_PATH" "$TARGET_BRANCH" >&2
else
    git -C "$GIT_ROOT" worktree add --no-track -b "$TARGET_BRANCH" "$WORKTREE_PATH" "$BASE_BRANCH" >&2
fi
[ $? -ne 0 ] && echo "Failed to create worktree (branch=$TARGET_BRANCH, base=$BASE_BRANCH)" >&2 && exit 1
cd "$WORKTREE_PATH" && pwd
