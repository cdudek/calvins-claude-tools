#!/usr/bin/env bash
# Usage: state-restart.sh <state_base> <revid>
#
# Sets up the per-revision run dir under a stable <state_base> (see state-dir.md)
# and prunes on start: keeps only the single newest PRIOR rev-dir, so a run holds
# exactly prior + current = 2 (bounds tmpfs growth). The caller then proceeds; the
# per-step skip-if-exists guards resume an interrupted run or cheaply re-render a
# complete one, so no fresh/resume branch is needed here.
#
# Output section:
#   -#-#- RESTART -#-#-
#   - state_dir: <state_base>/rev-<revid>
#   - revid: <revid>
#   - status: new | resuming        (informational only)
#   - pruned: <count of old rev-dirs removed>
set -euo pipefail

STATE_BASE="${1:?usage: state-restart.sh <state_base> <revid>}"
REVID="${2:?usage: state-restart.sh <state_base> <revid>}"

install -d -m 700 "$STATE_BASE"
target="$STATE_BASE/rev-$REVID"

# Prune-on-start: among existing rev-dirs other than the target, keep only the
# newest one (by mtime) and delete the rest. ls -dt is portable (GNU + BSD);
# `read` line by line splits only on newlines, so a $STATE_BASE containing spaces
# (e.g. a worktree dir with a space) can't word-split into a wrong rm -rf target.
# No mapfile and no array: macOS /bin/bash is 3.2, which lacks mapfile and trips
# `set -u` on an empty "${arr[@]}".
pruned=0
kept_prior=0
while IFS= read -r d; do
  d="${d%/}"
  [ "$d" = "$target" ] && continue
  if [ "$kept_prior" -eq 0 ]; then kept_prior=1; continue; fi
  rm -rf "$d"
  pruned=$((pruned + 1))
done < <(ls -dt "$STATE_BASE"/rev-*/ 2>/dev/null)

if [ -d "$target" ] && [ -n "$(ls -A "$target" 2>/dev/null)" ]; then
  status=resuming
else
  status=new
fi
install -d -m 700 "$target"

printf -- '-#-#- RESTART -#-#-\n'
printf -- '- state_dir: %s\n' "$target"
printf -- '- revid: %s\n' "$REVID"
printf -- '- status: %s\n' "$status"
printf -- '- pruned: %s\n' "$pruned"
