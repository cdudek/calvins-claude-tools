#!/usr/bin/env bash
# PostToolUse hook on Edit|Write: run the repo's formatter on the one file that changed
# (sdlc.json `lintOnEdit`: "<globs>": "<command with {file}>"), so formatting drift never
# accumulates to a red CI job. Scoped to the file, never the repo -- the playbook's rule
# for build-phase hooks is "fast and scoped to the file that changed".
# Always exits 0: a formatter failure is not a reason to fail the edit.
set -uo pipefail
set -f # the globs are patterns to match against the file name, never expanded against cwd
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
file=$(sdlc_field "$payload" file_path)
[ -n "$file" ] && [ -f "$file" ] || exit 0
rules=$(sdlc_get 'cfg["lintOnEdit"]') || exit 0
base=$(basename "$file")

while IFS=$'\t' read -r globs command; do
  [ -n "$globs" ] || continue
  for g in $globs; do
    # shellcheck disable=SC2254
    case "$base" in
      # The path is never interpolated into the command string: `{file}` becomes "$1"
      # and the path travels as an argument, so a name with quotes or `$(` cannot run.
      $g) cd "$SDLC_ROOT" && sh -c "${command//\{file\}/\"\$1\"}" _ "$file" >/dev/null 2>&1 || true; exit 0 ;;
    esac
  done
done < <(printf '%s' "$rules" | python3 -c 'import json,sys; [print(k+"\t"+v) for k,v in json.load(sys.stdin).items()]')
exit 0
