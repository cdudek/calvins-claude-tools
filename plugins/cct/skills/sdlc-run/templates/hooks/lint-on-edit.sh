#!/usr/bin/env bash
# PostToolUse hook on Edit|Write: run the repo's formatter on the one file that changed
# (sdlc.json `lintOnEdit`: "<globs>": "<command with {file}>"), so formatting drift never
# accumulates to a red CI job. Scoped to the file, never the repo -- the playbook's rule
# for build-phase hooks is "fast and scoped to the file that changed".
# Always exits 0: a formatter failure is not a reason to fail the edit.
# One interpreter start per call: file, then the rules as NUL-separated <globs>, <command>.
set -uo pipefail
set -f # the globs are patterns to match against the file name, never expanded against cwd
export PYTHONDONTWRITEBYTECODE=1 # a hook must not leave __pycache__ in a clean checkout
. "$(dirname "$0")/sdlc-config.sh"
: "${SDLC_PY:=python3}" # an older sdlc-config.sh (one-file upgrade) does not set it

fields=()
while IFS= read -r -d '' f; do fields+=("$f"); done < <(
  "$SDLC_PY" -c '
import json, sys
try:
    file = (json.load(sys.stdin).get("tool_input") or {}).get("file_path") or ""
    rules = json.load(open(sys.argv[1], encoding="utf-8")).get("lintOnEdit") or {}
    out = [file]
    for k, v in rules.items():
        out += [k, v]
except (OSError, ValueError, AttributeError, TypeError):
    sys.exit(0)
if file and rules:
    sys.stdout.write("\0".join(out) + "\0")
' "$SDLC_JSON" 2>/dev/null
)
[ "${#fields[@]}" -ge 3 ] || exit 0
file=${fields[0]}
[ -f "$file" ] || exit 0
base=$(basename "$file")

i=1
while [ "$i" -lt "${#fields[@]}" ]; do
  globs=${fields[$i]}
  command=${fields[$((i + 1))]}
  i=$((i + 2))
  [ -n "$globs" ] || continue
  for g in $globs; do
    # shellcheck disable=SC2254
    case "$base" in
      # The path is never interpolated into the command string: `{file}` becomes "$1"
      # and the path travels as an argument, so a name with quotes or `$(` cannot run.
      $g) cd "$SDLC_ROOT" && sh -c "${command//\{file\}/\"\$1\"}" _ "$file" >/dev/null 2>&1 || true; exit 0 ;;
    esac
  done
done
exit 0
