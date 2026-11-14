#!/usr/bin/env bash
# UserPromptSubmit hook: snapshot the source diff hash when the user sends a prompt, so
# verify-on-stop.sh can tell "this turn changed code" from "code was already dirty".
# Writes <git dir>/sdlc-turn-start.hash. Cheap and fail-open: any problem -> exit 0, no output.
set -uo pipefail
set -f # verifyDirty globs go to git as patterns, never expanded against cwd
. "$(dirname "$0")/sdlc-config.sh"

cat >/dev/null
cd "$SDLC_ROOT" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
globs=$(sdlc_get '" ".join(cfg["verifyDirty"])') || exit 0
gitdir=$(git rev-parse --absolute-git-dir 2>/dev/null) || exit 0
sdlc_diff_hash "$globs" >"$gitdir/sdlc-turn-start.hash" 2>/dev/null
exit 0
