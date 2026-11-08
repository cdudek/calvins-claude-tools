#!/usr/bin/env bash
# Safety regressions: dirty work stays, unpushed commits keep their branch,
# and a clean merged worktree is removed without affecting its neighbours.
set -euo pipefail
if [ "${WORKTREE_REMOVE_TEST_MODE:-}" = "" ]; then
    test_bin=$(mktemp -d)
    trap 'rm -rf "$test_bin"' EXIT
    for tool in bash cat jq git grep dirname mktemp rm; do
        ln -s "$(command -v "$tool")" "$test_bin/$tool"
    done
    WORKTREE_REMOVE_TEST_MODE=git PATH="$test_bin" bash "$0"
    if command -v wt >/dev/null 2>&1; then
        ln -s "$(command -v wt)" "$test_bin/wt"
        WORKTREE_REMOVE_TEST_MODE=wt PATH="$test_bin" bash "$0"
    fi
    exit 0
fi
HOOK="$(cd "$(dirname "$0")" && pwd)/worktree-remove.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
TMP=$(cd "$TMP" && pwd -P)
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
export WORKTRUNK_CONFIG_PATH="$TMP/no-config" WORKTRUNK_SYSTEM_CONFIG_PATH="$TMP/no-system-config"
git init -q -b main "$TMP/repo"
git -C "$TMP/repo" commit --allow-empty -qm initial
new() { git -C "$TMP/repo" worktree add -q --no-track -b "$1" "$TMP/repo/.worktrees/$1" main; }
remove() { printf '{"cwd":"%s","worktree_path":"%s"}' "$TMP/repo" "$TMP/repo/.worktrees/$1" | bash "$HOOK"; }
new dirty
printf tracked > "$TMP/repo/.worktrees/dirty/file"
git -C "$TMP/repo/.worktrees/dirty" add file
git -C "$TMP/repo/.worktrees/dirty" commit -qm tracked
printf changed > "$TMP/repo/.worktrees/dirty/file"
if remove dirty >"$TMP/out" 2>"$TMP/err"; then echo 'FAIL dirty tracked worktree removed'; exit 1; fi
grep -q 'dirty worktree' "$TMP/err"
test "$(cat "$TMP/repo/.worktrees/dirty/file")" = changed
git -C "$TMP/repo" show-ref --verify --quiet refs/heads/dirty
echo 'ok dirty tracked worktree and branch kept'
new untracked
printf unique > "$TMP/repo/.worktrees/untracked/untracked-file"
if remove untracked >"$TMP/out" 2>"$TMP/err"; then echo 'FAIL untracked worktree removed'; exit 1; fi
test "$(cat "$TMP/repo/.worktrees/untracked/untracked-file")" = unique
git -C "$TMP/repo" show-ref --verify --quiet refs/heads/untracked
echo 'ok untracked files and branch kept'
new ignored
printf '.ignored-local\n' >> "$TMP/repo/.git/info/exclude"
printf unique > "$TMP/repo/.worktrees/ignored/.ignored-local"
if remove ignored >"$TMP/out" 2>"$TMP/err"; then echo 'FAIL ignored untracked worktree removed'; exit 1; fi
test -f "$TMP/repo/.worktrees/ignored/.ignored-local"
echo 'ok ignored untracked files kept'
new unpushed
git -C "$TMP/repo/.worktrees/unpushed" commit --allow-empty -qm unpushed
unpushed=$(git -C "$TMP/repo/.worktrees/unpushed" rev-parse HEAD)
remove unpushed >"$TMP/out" 2>"$TMP/err"
test "$(git -C "$TMP/repo" rev-parse refs/heads/unpushed)" = "$unpushed"
grep -q 'branch unpushed kept' "$TMP/err"
echo 'ok unpushed commit branch kept'
new merged
git -C "$TMP/repo/.worktrees/merged" commit --allow-empty -qm merged
git -C "$TMP/repo" merge --ff-only -q merged
remove merged >"$TMP/out" 2>"$TMP/err"
test ! -e "$TMP/repo/.worktrees/merged"
if git -C "$TMP/repo" show-ref --verify --quiet refs/heads/merged; then echo 'FAIL merged branch retained'; exit 1; fi
test -f "$TMP/repo/.worktrees/dirty/file"
test -f "$TMP/repo/.worktrees/untracked/untracked-file"
echo 'ok clean merged worktree and branch removed; neighbours kept'
