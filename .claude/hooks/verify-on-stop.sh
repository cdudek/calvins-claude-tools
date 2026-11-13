#!/usr/bin/env bash
# Stop hook: "done" means verify passed. If the session is about to stop with uncommitted
# source changes (sdlc.json `verifyDirty` globs), run exactly what CI runs (`verify`);
# on failure, block the stop and hand the tail back to Claude so it fixes the code
# before reporting.
#
# Cheap by construction: nothing dirty -> exit 0 in well under a second. Honours
# stop_hook_active so a failing verify can never loop the session forever.
#
# Two more skips keep it from re-running a check nobody asked for (leadhub: 760 runs, 2.5 h of
# them after turns that changed nothing):
#   - inside an active /goal the milestone gate (verify_gate.py) is the check, so exit 0. The
#     signal is the one chain-gate.sh uses: the last `goal_status` attachment of the transcript
#     says met=false. An unreadable transcript fails open, i.e. verify still runs.
#   - the dirty diff (`git diff HEAD` plus untracked verifyDirty files) hashes to what the last
#     passing run saw, kept in the git dir.
set -uo pipefail
set -f # verifyDirty globs go to git as patterns, never expanded against cwd
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
[ "$(sdlc_field "$payload" stop_hook_active)" = "true" ] && exit 0

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

stamp="$(git rev-parse --absolute-git-dir)/sdlc-verify-stop.hash"
now=$(
  {
    git diff HEAD 2>/dev/null
    for g in $globs; do
      git ls-files --others --exclude-standard -- "$g" | while IFS= read -r f; do
        printf '%s\n' "$f"
        cat "$f"
      done
    done
  } | git hash-object --stdin
)
[ -f "$stamp" ] && [ "$(cat "$stamp")" = "$now" ] && exit 0

if out=$(eval "$verify" 2>&1); then
  printf '%s\n' "$now" >"$stamp"
  exit 0
fi
{
  echo "verify-on-stop FAILED (\`$verify\`) with uncommitted source changes -- fix the code, not the test, then stop again:"
  printf '%s\n' "$out" | tail -40
} >&2
exit 2
