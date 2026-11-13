#!/usr/bin/env bash
# PreToolUse hook on Bash: block what sdlc.json `blocked[]` names -- dependency changes,
# cluster writes, database pushes -- each with the route a human takes instead.
#
# Exit 2 blocks the call and sends stderr to Claude, which then tells the user the
# route. Everything else exits 0 untouched. A block explains itself (playbook rule).
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
cmd=$(sdlc_field "$payload" command)
[ -n "$cmd" ] || exit 0
blocked=$(sdlc_get 'cfg["blocked"]') || exit 0
docs=$(sdlc_get 'cfg["docs"]' || echo "docs/sdlc.md")

# One rule per line: <regex>\t<message>. Tabs never appear in either.
while IFS=$'\t' read -r match message; do
  [ -n "$match" ] || continue
  if printf '%s' "$cmd" | grep -Eq -- "$match"; then
    printf 'BLOCKED: %s\n(%s, "Hooks")\n' "$message" "$docs" >&2
    exit 2
  fi
done < <(printf '%s' "$blocked" | python3 -c 'import json,sys; [print(r["match"]+"\t"+r["message"]) for r in json.load(sys.stdin)]')
exit 0
