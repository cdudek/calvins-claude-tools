#!/usr/bin/env bash
# Stop hook: "done" means verify passed. If a turn changed uncommitted source (sdlc.json
# `verifyDirty` globs), run exactly what CI runs (`verify`); on failure, block the stop and
# hand the tail back to Claude so it fixes the code before reporting.
#
# Runs only after a turn that changed code. Order, cheapest first, each step exits 0:
#   1. stop_hook_active (a failing verify can never loop the session forever)
#   2. no git, no sdlc.json, nothing dirty under verifyDirty
#   3. the diff hash equals the snapshot turn-start.sh took at prompt submit: this turn changed
#      nothing (a chat turn, or work that was already uncommitted)
#   4. the diff hash was already verified, pass OR fail (stamp in the git dir): a red state is
#      not re-run and not blocked again until the code changes
#   5. inside an active /goal the milestone gate (verify_gate.py) is the check. The signal is
#      the one chain-gate.sh uses: the last `goal_status` attachment of the transcript says
#      met=false. It parses the whole transcript, so it runs last. Unreadable -> verify runs.
# A missing turn-start snapshot (first turn after an upgrade) skips step 3 only.
set -uo pipefail
set -f # verifyDirty globs go to git as patterns, never expanded against cwd
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
[ "$(sdlc_field "$payload" stop_hook_active)" = "true" ] && exit 0

cd "$SDLC_ROOT" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
verify=$(sdlc_get 'cfg.get("verifyStop") or cfg["verify"]') || exit 0
globs=$(sdlc_get '" ".join(cfg["verifyDirty"])') || exit 0

dirty=""
for g in $globs; do
  dirty=$(git status --porcelain -- "$g" 2>/dev/null | head -1)
  [ -n "$dirty" ] && break
done
[ -z "$dirty" ] && exit 0

gitdir=$(git rev-parse --absolute-git-dir 2>/dev/null) || exit 0
now=$(sdlc_diff_hash "$globs")
[ -n "$now" ] || exit 0
start="$gitdir/sdlc-turn-start.hash"
[ -f "$start" ] && [ "$(cat "$start")" = "$now" ] && exit 0
# The stamp is "<hash> pass|fail"; an older hook wrote the bare hash of a passing run.
stamp="$gitdir/sdlc-verify-stop.hash"
[ -f "$stamp" ] && [ "$(cut -d' ' -f1 "$stamp")" = "$now" ] && exit 0

transcript=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("transcript_path",""))' 2>/dev/null)
if [ -n "$transcript" ] && python3 - "$transcript" <<'PY' 2>/dev/null
import json, sys
last = None
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        att = json.loads(line).get("attachment")
    except (ValueError, AttributeError):
        continue
    if isinstance(att, dict) and att.get("type") == "goal_status":
        last = att
sys.exit(0 if last is not None and last.get("met") is False else 1)
PY
then exit 0; fi

if out=$(eval "$verify" 2>&1); then
  printf '%s pass\n' "$now" >"$stamp"
  exit 0
fi
printf '%s fail\n' "$now" >"$stamp"
{
  echo "verify-on-stop FAILED (\`$verify\`) with uncommitted source changes -- fix the code, not the test, then stop again:"
  printf '%s\n' "$out" | tail -40
} >&2
exit 2
