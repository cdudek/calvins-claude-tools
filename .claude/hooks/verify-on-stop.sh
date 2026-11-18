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
#      read by goal_active.py, the one reading chain-gate.sh and pr-gate.sh share. It parses the
#      whole transcript, so it runs last. Unreadable -> verify runs. No helper -> exit 2.
# A missing turn-start snapshot (first turn after an upgrade) skips step 3 only.
# Interpreter starts: one on every Stop (payload + sdlc.json), a second only at step 5, on the
# path that is about to run `verify` for seconds anyway.
set -uo pipefail
set -f # verifyDirty globs go to git as patterns, never expanded against cwd
. "$(dirname "$0")/sdlc-config.sh"
: "${SDLC_PY:=python3}" # an older sdlc-config.sh (one-file upgrade) does not set it

# One interpreter start for the whole hot path: the payload and sdlc.json are read together and
# come back as NUL-separated fields -- stop_hook_active, transcript_path, verify, verifyDirty globs.
fields=()
while IFS= read -r -d '' f; do fields+=("$f"); done < <(
  "$SDLC_PY" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    d = {}
if not isinstance(d, dict):
    d = {}
out = ["true" if d.get("stop_hook_active") is True else "false", d.get("transcript_path") or ""]
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    out += [cfg.get("verifyStop") or cfg["verify"], " ".join(cfg["verifyDirty"])]
except (OSError, ValueError, KeyError, TypeError, AttributeError):
    out += ["", ""]
sys.stdout.write("\0".join(out) + "\0")
' "$SDLC_JSON" 2>/dev/null
)
[ "${#fields[@]}" -ge 4 ] || exit 0
[ "${fields[0]}" = "true" ] && exit 0
transcript=${fields[1]}
verify=${fields[2]}
globs=${fields[3]}
[ -n "$verify" ] && [ -n "$globs" ] || exit 0

cd "$SDLC_ROOT" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

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

# goal_active.py exits 0 when a goal runs; 1 for none or an unreadable transcript (verify runs).
helper="$(dirname "$0")/goal_active.py"
if [ ! -f "$helper" ]; then
  echo "verify-on-stop: goal_active.py is missing beside this hook; run \`sdlc-run adopt\` to restore it." >&2
  exit 2
fi
if [ -n "$transcript" ] && python3 "$helper" "$transcript" 2>/dev/null; then exit 0; fi

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
