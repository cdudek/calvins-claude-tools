#!/usr/bin/env bash
# PreToolUse hook on Bash: block what sdlc.json `blocked[]` names -- dependency changes,
# cluster writes, database pushes -- each with the route a human takes instead.
#
# Exit 2 blocks the call and sends stderr to Claude, which then tells the user the
# route. Everything else exits 0 untouched. A block explains itself (playbook rule).
#
# One interpreter start per call: it parses the payload and sdlc.json and prints the command,
# the docs path and the rules as NUL-separated fields. The matching stays `grep -E`, because the
# rules are POSIX ERE (`[[:space:]]`), which Python's `re` does not read.
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
fields=()
while IFS= read -r -d '' f; do fields+=("$f"); done < <(
  printf '%s' "$payload" | "$SDLC_PY" -c '
import json, sys
try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    rules = cfg.get("blocked") or []
    out = [cmd, cfg.get("docs") or "docs/sdlc.md"]
    for r in rules:
        out += [r["match"], r.get("message", "")]
except (OSError, ValueError, KeyError, AttributeError, TypeError):
    sys.exit(0)
if cmd and rules:
    sys.stdout.write("\0".join(out) + "\0")
' "$SDLC_JSON" 2>/dev/null
)
[ "${#fields[@]}" -ge 4 ] || exit 0
cmd=${fields[0]}
docs=${fields[1]}

# One rule per field pair: <regex>, <message>.
i=2
while [ "$i" -lt "${#fields[@]}" ]; do
  match=${fields[$i]}
  message=${fields[$((i + 1))]}
  i=$((i + 2))
  [ -n "$match" ] || continue
  if printf '%s' "$cmd" | grep -Eq -- "$match"; then
    text=$(printf 'BLOCKED: %s\n(%s, "Hooks")' "$message" "$docs")
    # a repeat of this block says STOP (block_state.py); without the helper the text is plain
    out=$(printf '%s' "$payload" | python3 "$(dirname "$0")/block_state.py" gate-bash.sh "sdlc.json blocked[]" "$message" "$text" 2>/dev/null) && [ -n "$out" ] && text=$out
    printf '%s\n' "$text" >&2
    exit 2
  fi
done
exit 0
