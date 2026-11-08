#!/usr/bin/env bash
# Falsifiable test for the WorktreeCreate hook. Exit non-zero on failure.
#
# Self-contained: a throwaway repo with a bare "origin" whose master is one commit
# AHEAD of the local checkout, so "based on origin/master" and "based on the main
# checkout" give different answers.

set -uo pipefail
# Run the same behavioural assertions with and without the Worktrunk executable.
if [ "${WORKTREE_TEST_MODE:-}" = "" ]; then
    test_bin=$(mktemp -d)
    trap 'rm -rf "$test_bin"' EXIT
    for tool in bash cat jq git xargs sh sed mkdir grep dirname date; do
        ln -s "$(command -v "$tool")" "$test_bin/$tool"
    done
    WORKTREE_TEST_MODE=git PATH="$test_bin" bash "$0" || exit 1
    if command -v wt >/dev/null 2>&1; then
        ln -s "$(command -v wt)" "$test_bin/wt"
        WORKTREE_TEST_MODE=wt PATH="$test_bin" bash "$0" || exit 1
    fi
    exit 0
fi
DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$DIR/worktree-create.sh"
fail=0

TMP=$(/usr/bin/mktemp -d)
TMP=$(cd "$TMP" && pwd -P)
trap '/bin/rm -rf "$TMP"' EXIT
export WORKTRUNK_CONFIG_PATH="$TMP/no-user-config" WORKTRUNK_SYSTEM_CONFIG_PATH="$TMP/no-system-config"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

git init -q -b master "$TMP/origin.git" --bare
git init -q -b master "$TMP/repo"
cd "$TMP/repo"
echo one > f && git add f && git commit -q -m one
git remote add origin "$TMP/origin.git"
git push -q -u origin master
# origin moves on; the local checkout stays stale (and on a side branch, like a
# developer mid-work).
git clone -q "$TMP/origin.git" "$TMP/other" && (cd "$TMP/other" && echo two > g && git add g && git commit -q -m two && git push -q)
git checkout -q -b some/old-branch

run() { printf '{"name":"%s","cwd":"%s"}' "$1" "$TMP/repo" | bash "$HOOK"; }

check() { # $1 label, $2 condition
    if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi
}

out=$(run my-feature)
check "a bare name lands in <repo>/.worktrees/<name>" '[ "$out" = "$TMP/repo/.worktrees/my-feature" ]'
check "the branch is named after the worktree" '[ "$(git -C "$out" rev-parse --abbrev-ref HEAD)" = "my-feature" ]'
check "the base is origin/master, not the stale main checkout" '[ -f "$out/g" ]'
check "the branch does not track master" '! git -C "$out" config branch.my-feature.merge > /dev/null'

out2=$(run my-feature)
check "re-entering an existing worktree returns it, no recreate" '[ "$out2" = "$TMP/repo/.worktrees/my-feature" ]'

out3=$(run "@feat/login")
check "@branch lands at .worktrees/<last segment>" '[ "$out3" = "$TMP/repo/.worktrees/login" ]'
check "@branch checks out that branch" '[ "$(git -C "$out3" rev-parse --abbrev-ref HEAD)" = "feat/login" ]'

git -C "$TMP/repo" branch -q old-base HEAD
out4=$(run "x@feat/x@old-base")
check "an explicit base is honoured" '[ ! -f "$out4/g" ]'

out5=$(run "./elsewhere/y")
check "a path is reduced to its basename under .worktrees/" '[ "$out5" = "$TMP/repo/.worktrees/y" ]'

out6=$(cd "$out5" && echo "{\"name\":\"z\",\"cwd\":\"$out5\"}" | bash "$HOOK" 2>"$TMP/err6")
check "a worktree made from inside a worktree never nests" '[ "$(cd "$out6" && pwd -P)" = "$(cd "$TMP/repo" && pwd -P)/.worktrees/z" ]'
check "the hook runs without errors from inside a worktree" '! grep -iE "fatal:|error:|failed" "$TMP/err6"'

check "no sibling worktree was ever created" '[ ! -e "$TMP/my-feature" ] && [ ! -e "$TMP/login" ]'

# Removal must target only this worktree; its neighbour survives.
printf '{"worktree_path":"%s","cwd":"%s"}' "$out3" "$TMP/repo" | bash "$DIR/worktree-remove.sh"
check "the owned worktree is removed" '[ ! -e "$out3" ]'
check "its unmerged branch is kept" 'git show-ref --verify --quiet refs/heads/feat/login'
check "neighbour worktrees survive cleanup" '[ -f "$out/g" ] && [ -d "$out4" ]'

# Installed Worktrunk errors must never trigger a plain Git retry.
mkdir -p "$TMP/failing-bin"
printf '#!/bin/sh\nexit 17\n' > "$TMP/failing-bin/wt"
/bin/chmod +x "$TMP/failing-bin/wt"
if PATH="$TMP/failing-bin:$PATH" run wt-error >"$TMP/wt-out" 2>"$TMP/wt-err"; then
    echo "FAIL a failed Worktrunk call must stop"; fail=1
fi
check "Worktrunk failure never creates a fallback branch" '! git show-ref --verify --quiet refs/heads/wt-error && [ ! -e "$TMP/repo/.worktrees/wt-error" ]'

# A failed fetch must not create a branch from stale origin/master.
git remote set-url origin "$TMP/missing.git"
if run no-stale >"$TMP/stale-out" 2>"$TMP/stale-err"; then
    echo "FAIL a failed fetch must stop creation"; fail=1
fi
check "no branch or worktree was created from stale refs" '! git show-ref --verify --quiet refs/heads/no-stale && [ ! -e "$TMP/repo/.worktrees/no-stale" ]'
exit $fail
